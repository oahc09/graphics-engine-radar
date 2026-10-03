# Graphics Engine Radar public-deployment fix summary

## Implemented

1. **Admin boundary** — default admin API disabled/not registered; FastAPI route-level Bearer guard remains mandatory if explicitly enabled; Next `/api/*` changed from catch-all proxy to a public-read allowlist.
2. **Error privacy** — public object details no longer serialize `last_error`; generic 500 responses use stable safe fields/request id; server log detail is redacted and no traceback is reflected.
3. **SSR/API addressing** — server-side fetch requires runtime `INTERNAL_API_BASE`; browser defaults to same-origin `/api`; the public `/api/*` proxy is a runtime Route Handler with an explicit read-only allowlist, so `next build` no longer requires an API address. Production runtime without an internal target returns a safe 503 rather than baking loopback/internal DNS into the image.
4. **Single pipeline entry** — Click invoked with `standalone_mode=False`; normal return proceeds, explicit non-zero Click return is converted to failure, exceptions/non-zero exits stop dependent stages and return non-zero.
5. **Continuous scheduler** — dedicated scheduler calls only the single pipeline entry, bounded timeout/retry, PostgreSQL advisory lock, durable run/scheduler state, stale `running` recovery after process restart.
6. **Dependency security** — Next 15.4.5 → 15.5.27; React/React DOM 19.1.0 → 19.1.9; npm lock updated; Docker Web build switched to `npm ci`.
7. **Runtime boundary** — DB/Redis/API/scheduler are not host-published; only Web binds, and defaults to `127.0.0.1` pending an authorized TLS reverse proxy. Added DB/API/Web/scheduler health checks and migration gate.
8. **Operations** — added configuration example, migration, health/restart model, backup/restore and rollback runbook.

## Confirmed baseline defects vs hardening

Confirmed at baseline: unauthenticated admin routes, public `last_error`, loopback SSR fallback/build-time API baking, Click pipeline interruption, vulnerable frontend versions, absence of full scheduler.

Hardening added without claiming a reproduced exploit: private service exposure, explicit readiness, persistent scheduler state, stale-run recovery, migration gate, bounded retries, backup/rollback procedures, redacted logs.

Still environment/production dependent: concrete TLS termination, domain/DNS, firewall, trusted proxy config, external rate limits, resource limits, log retention, production backup destination/RPO/RTO, immutable image digests and image scan.
