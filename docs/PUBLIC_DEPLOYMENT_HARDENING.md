# Public deployment hardening / runbook

Baseline reviewed: `3e80d4903915ade225dc89b4f97e1adac7cc4d2b`.
This document prepares the repository for deployment; it is not evidence that a public host, DNS name, TLS certificate, or external smoke test exists.

## Security boundary

The default production shape is public read-only Web. PostgreSQL, Redis and FastAPI have no host port mapping in Compose. The Web container reaches FastAPI through `http://api:8300`; server-side rendering uses `INTERNAL_API_BASE`, while browser requests use the same-origin `/api/*` allowlist. `/api/admin/*` is not proxied.

Admin routes are not registered unless `ENABLE_ADMIN_API=true`. Even when enabled, every admin route requires `Authorization: Bearer <ADMIN_API_TOKEN>` at FastAPI itself. Missing admin configuration fails closed. Do not place this token in `NEXT_PUBLIC_*`, a URL, image build args, or browser storage. Remote admin additionally requires an approved TLS/reverse-proxy design; the default recommendation remains disabled admin.

Public unhandled errors contain only a stable error id/message/request id. `Source.last_error` remains an internal database field and is not serialized by the public object endpoint. Server error logs use request correlation and redact common credential/connection-string forms.

## Configuration

Copy `.env.example` to a local secret-managed environment file only in the actual target environment. This repository does not generate credentials. Compose requires `POSTGRES_PASSWORD` and `DATABASE_URL`; this is deliberate so it cannot silently boot with a public default database password.

`GITHUB_TOKEN` is optional. `LLM_API_KEY` is optional and should remain empty for the required zero-cost deterministic heuristic path. Do not select `claude-cli` or `codex-cli` in unattended deployment unless separately approved.

## Start / migrate

```bash
docker compose config
docker compose build --pull
docker compose up -d postgres redis
docker compose run --rm migrate
docker compose up -d api scheduler web
docker compose ps
```

`migrate` must complete successfully before API/scheduler start. Migration failures block startup. Do not run multiple schema migrators concurrently.

## Full pipeline

Manual and scheduled execution use the same entrypoint:

```bash
docker compose exec scheduler uv run --no-dev python scripts/pipeline.py
```

Stages are collect → intelligence → trends → daily/weekly/monthly digest. Click commands run with `standalone_mode=False`; a stage exception returns a non-zero pipeline exit and stops dependent stages. A PostgreSQL session advisory lock prevents overlapping complete runs across processes/hosts using the same database. Lock contention returns exit 75 and does not start a second run.

`pipeline_runs` records run id, stage and terminal state. After a process crash the PostgreSQL session lock is released by connection loss; the next lock owner marks any stale `running` row `abandoned` with `PROCESS_RESTART`. `scheduler_state` records next run, last success/failure and exit code. Scheduler retry count and timeout are bounded by environment variables.

Individual collector-source failures remain visible in collector counts/internal source state and do not automatically fail the entire batch; this preserves the existing “one bad source does not stop all sources” behavior. A command/stage-level failure fails the complete run.

## Health

- PostgreSQL: `pg_isready`.
- API readiness: `/health` executes `SELECT 1`; `/health/live` is process liveness only.
- Web: HTTP request to the local Next server.
- Scheduler: durable `scheduler_state.updated_at` freshness, bounded by interval + pipeline timeout + grace.

A process being alive is not equivalent to fresh data. Monitor `scheduler_state`, latest successful `pipeline_runs.finished_at`, and business-data timestamps.

## Backup and restore

Choose retention/RPO/RTO and an authorized backup destination before production. Do not upload database dumps to an unapproved service.

Example local/private backup:

```bash
mkdir -p backups
umask 077
docker compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "backups/radar-$(date +%Y%m%d-%H%M%S).dump"
```

Restore rehearsal must use an isolated database, not the live database:

```bash
docker compose exec -T postgres createdb -U "$POSTGRES_USER" radar_restore_test
docker compose exec -T postgres pg_restore \
  -U "$POSTGRES_USER" -d radar_restore_test --clean --if-exists < backups/<file>.dump
docker compose exec -T postgres psql -U "$POSTGRES_USER" -d radar_restore_test \
  -c 'SELECT count(*) FROM objects;' \
  -c 'SELECT count(*) FROM sources;' \
  -c 'SELECT count(*) FROM events;' \
  -c 'SELECT count(*) FROM pipeline_runs;'
```

Record dump checksum, start/end time, row-count sanity checks, schema revision and restore duration. In the present execution environment Docker/PostgreSQL were unavailable, so this rehearsal is a required blocked item, not a completed result.

## Rollback

Code/image rollback and schema rollback are separate decisions. Before rolling back application images, inspect the migration delta and compatibility. This change adds only `pipeline_runs` and `scheduler_state`; the Alembic downgrade removes those operational tables, which also deletes their history. Do not run downgrade on production merely because an application image is rolled back.

Typical application-only rollback, when the prior image is schema-compatible:

```bash
docker compose stop web api scheduler
# restore the previously approved image/tag or code revision
docker compose up -d api scheduler web
```

Never use `docker compose down -v` as a rollback; it deletes the database volume.

## Still required before public release

A concrete host/domain and authorization are still required for: public bind/firewall rules, TLS termination and renewal, trusted proxy headers, external rate limiting/DoS controls, production log retention, resource limits, backup destination/retention, alert delivery, RPO/RTO, and an external smoke test. Only the Web/TLS entrypoint should be public; database/Redis remain private. Whether FastAPI itself gets a public read-only route should be decided explicitly rather than inferred from Compose.
