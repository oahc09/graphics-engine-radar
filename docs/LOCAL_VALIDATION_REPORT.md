# Local validation report — final isolated patch state

Date: 2026-10-02
Baseline remote `main`: `3e80d4903915ade225dc89b4f97e1adac7cc4d2b`
Workspace: isolated reconstructed patch workspace; no GitHub write, PR, push, public deployment, credential creation, or persistent access change was performed.

## Environment

- Python 3.13.5
- uv 0.10.0
- Node v22.16.0
- npm 10.9.2
- Docker/Compose: unavailable
- PostgreSQL client / pg_restore: unavailable
- External package DNS: unavailable

## Results

| Check | Command / method | Result | Evidence / limitation |
| --- | --- | --- | --- |
| New security/deployment regression suite | `pytest -q tests/test_public_deployment_fixes.py` | PASS | 21 passed. Covers admin auth guard, public error redaction, build-without-runtime-API config, runtime proxy allowlist/GET-only boundary, SSR no-loopback config, Click normal/failure/explicit exit, stage stop, advisory-lock contention, bounded retry, restart state model, Compose exposure/health structure. |
| Python syntax | `python -m py_compile apps/api/radar_api/*.py scripts/*.py packages/domain/radar_domain/pipeline_state.py migrations/versions/20261002_add_pipeline_runs.py` | PASS | No syntax errors. |
| Next config syntax | `node --check apps/web/next.config.mjs` | PASS | No syntax error. |
| Compose YAML structure | PyYAML parse + service/exposure assertions | PASS (static) | Services parse; postgres/API/scheduler have no host `ports`. Docker Compose semantic validation unavailable. |
| npm lock consistency | Node JSON check | PASS (static) | package.json root deps match lock root; resolved Next/React versions are 15.5.27/19.1.9. |
| `npm ci` / production build | `npm install --package-lock-only --offline ...` attempted; registry unavailable | BLOCKED | npm returned `ENOTCACHED`; environment has no registry DNS. No final production-build PASS claimed. |
| Existing 28 Python tests | Not rerun | BLOCKED | Full repository was not mountable/clonable in this execution container; only read-only GitHub source access was available. Prior 28-pass result remains baseline evidence only. |
| Real API + PostgreSQL integration | Not run | BLOCKED | Docker/PostgreSQL/pgvector runtime unavailable. |
| Cross-container first-response SSR | Not run | BLOCKED | Docker unavailable. Source/config regression is covered, but no container claim is made. |
| One real no-key full pipeline | Not run | BLOCKED | Full repo + PostgreSQL unavailable. Existing heuristic implementation was not modified; no paid LLM was enabled. |
| Scheduler two cycles / concurrent real runs / restart during run | Not run against PostgreSQL | BLOCKED | Unit regression covers lock contention/retry/restart-state logic; real process/container behavior still requires Docker/PostgreSQL. |
| Migration from empty/baseline DB | Not run | BLOCKED | Docker/PostgreSQL unavailable. Migration file syntax only. |
| Backup/restore rehearsal | Not run | BLOCKED | `pg_dump`/`pg_restore` and PostgreSQL unavailable. Runbook contains exact rehearsal procedure. |
| Image/Python vulnerability scan | Not run | BLOCKED | `pip-audit`, `trivy`, `grype` unavailable and advisory/package network blocked. |
| TLS/domain/public firewall/external smoke | Not run | BLOCKED BY SCOPE | No authorized production server/domain. |

## Regression detail

A new test exposed a real Click edge case during this execution: with `standalone_mode=False`, `ctx.exit(7)` returns integer `7` instead of raising. The first pipeline implementation ignored that return and would have continued. The implementation was corrected so `_invoke_click` converts any non-zero integer result into `click.exceptions.Exit`; the complete pipeline returns that non-zero exit and stops later stages. Final regression suite now passes 21/21 after the additional Next build/runtime-address regression.

## Secret/redaction evidence

Repository scan found only deliberately fake test markers (`unit-test-secret`, `postgresql://u:p@internal...`) inside tests. No generated real token/key/password was created. The public error regression proves those markers are absent from the HTTP response, and the redaction helper removes credential/connection-string patterns from controlled logs.

## Next build/runtime API address correction

A follow-up source review found that the previous `next.config.mjs` required `API_PROXY_TARGET`/`INTERNAL_API_BASE` whenever `NODE_ENV=production`, while `docker/web.Dockerfile` runs `npm run build` before Compose runtime environment variables exist. That was a valid build-time risk. The fix removes runtime upstream resolution from `next.config.mjs` and moves the public `/api/*` proxy to `app/api/[...path]/route.ts`. The route handler reads the internal target at request time, exposes only the explicit public GET allowlist, returns 404 for non-allowlisted paths and 503 when runtime target configuration is absent.

Verified locally: `NODE_ENV=production` with both API target variables unset can import `next.config.mjs` successfully; the regression suite passes 21/21. Full `docker compose build --no-cache web` remains blocked in this execution environment because Docker is not installed, so no container-build PASS is claimed here.
