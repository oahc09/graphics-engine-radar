# Security version evidence — 2026-10-02

## Frontend dependency decision

- Baseline: Next.js `15.4.5`, React/React DOM `19.1.0`.
- Next.js official September 30, 2026 security release: Maintenance LTS `15.5.27` is the patched 15.x target; `16.3.8` is Active LTS. This patch keeps the existing major/minor architecture and moves to `15.5.27` rather than introducing a major-version migration.
- React official July 21, 2026 advisory GHSA-wx67-qw84-cm4g lists `19.1.0` through `19.1.8` as affected and `19.1.9` as patched for the Server Functions DoS issue. React releases list `19.1.9` on July 21, 2026.
- Result: `next=15.5.27`, `react=19.1.9`, `react-dom=19.1.9`; package-lock package records and integrity hashes were updated from published npm lock data and root/lock consistency was checked locally.

Official references:

- https://nextjs.org/blog — September 30, 2026 Security Release
- https://github.com/react/react/security/advisories/GHSA-wx67-qw84-cm4g
- https://github.com/react/react/releases

## Python and container dependencies

The baseline `uv.lock` was reviewed read-only and was not changed by this patch. A fresh vulnerability audit could not be executed because this environment has neither network access to advisory/package services nor `pip-audit`, `trivy`, or `grype`. Therefore Python dependency and image vulnerability status is **unverified**, not “clean”.

Container bases remain the project families `python:3.12-slim`, `node:22-alpine`, `pgvector/pgvector:pg17`, and `redis:7-alpine`. A production build should use `--pull` and record immutable image digests plus an image vulnerability scan in the target CI/registry before release. Do not claim a mutable tag is a security attestation.
