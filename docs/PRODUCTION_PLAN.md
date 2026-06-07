# Production Hardening — Story Plan

Turns [`PRODUCTION_READINESS.md`](./PRODUCTION_READINESS.md) into independently
shippable, test-driven stories (same red→green→refactor discipline as the
feature work). Implemented **one per PR**, in roughly this order.

Status: `todo` · `in-progress` · `done`

---

## P0 — Blockers

### PR0-1 — CORS · `done`
*Browser frontend can call the API cross-origin.*
- AC1: configured origins get `Access-Control-Allow-Origin`; unknown origins don't.
- AC2: origins come from `CORS_ORIGINS` (default `http://localhost:3000`).

### PR0-2 — Centralized config + secret validation · `todo`
*All config in one validated place; refuse to boot insecurely.*
- AC1: a pydantic `Settings` object reads every env var (DB, auth, hosts, storage, CORS).
- AC2: startup fails fast if `AUTH_SECRET` is unset/default while `ENV=production`.
- AC3: existing modules read settings instead of `os.environ` scattered around.

### PR0-3 — PostgreSQL support · `todo`
*Run on Postgres, not just SQLite.*
- AC1: `DATABASE_URL` drives the engine; Postgres works (psycopg).
- AC2: SQLite-only assumptions removed; tests still run on SQLite.

### PR0-4 — Alembic migrations · `todo`
*Schema is migration-managed, not `create_all`.*
- AC1: Alembic configured; an initial migration captures the current schema.
- AC2: app startup no longer calls `create_all`; a documented `alembic upgrade head` step exists.
- AC3: `Project.owner_id` tightened to `NOT NULL` via migration.

### PR0-5 — Background job worker · `todo`
*Generation runs off the request thread; GPU work serialized.*
- AC1: `execute_job` enqueues to a worker (RQ/Redis or a DB-backed worker) and returns immediately (`queued`).
- AC2: a single worker processes jobs FIFO (serializes GPU); status/progress update live.
- AC3: endpoints that generate (clip, later keyframe) return a job, not a blocking call.

### PR0-6 — Authenticated media serving · `todo`
*Fetch the actual bytes (keyframes, clips, final MP4) over HTTP.*
- AC1: `GET /scenes/{id}/keyframe/file`, `.../clip/file`, `GET /projects/{id}/render/file` stream the asset to the owner.
- AC2: non-owners get 404; missing asset gives a clear error.
- AC3: frontend links to these instead of raw filesystem paths.

### PR0-7 — Upload size limits · `todo`
- AC1: audio/video/image uploads over a configurable cap are rejected (413).

### PR0-8 — Production frontend build · `todo`
- AC1: `frontend/Dockerfile` uses `next build && next start`.
- AC2: `NEXT_PUBLIC_API_URL` is build-time configurable; documented per-env.

### PR0-9 — Reverse proxy + TLS (deploy artifact) · `todo`
- AC1: a sample proxy config (Caddy/nginx) terminates TLS and routes `/api` → backend, `/` → frontend.

---

## P1 — Important

### PR1-1 — Auth hardening · `todo`
- AC1: rate-limit `/auth/login` + `/auth/register`.
- AC2: refresh tokens or server-side revocation; access tokens short-lived.
- AC3: frontend intercepts 401 → clear token + redirect to `/login`.

### PR1-2 — Structured logging + request IDs · `todo`
- AC1: JSON logs with a per-request id; job lifecycle logged.

### PR1-3 — Error tracking · `todo`
- AC1: Sentry (or similar) wired on backend + frontend, opt-in via DSN env.

### PR1-4 — Readiness probe · `todo`
- AC1: `GET /ready` checks DB connectivity (and optionally model servers); `/health` stays liveness-only.

### PR1-5 — Per-user quotas · `todo`
- AC1: configurable caps on generation jobs / projects per user; over-limit → 429.
- AC2: enforcement reads the existing usage metering.

### PR1-6 — Pagination · `todo`
- AC1: `GET /projects`, `/scenes`, `/projects/{id}/jobs` accept `limit`/`offset` (or cursor) with sane defaults/caps.

### PR1-7 — CI publish + deploy · `todo`
- AC1: build and push versioned images (GHCR) on tag/merge.
- AC2: a deploy workflow runs `alembic upgrade head` then rolls out.
- AC3: dependency + secret scanning (pip-audit, npm audit, gitleaks).

### PR1-8 — Real-path integration smoke tests · `todo`
- AC1: opt-in tests exercise real FFmpeg render, librosa analysis, and an Ollama/ComfyUI happy path (marked, not in the default unit run).

---

## P2 — Hardening & scale

### PR2-1 — Object storage backend · `todo`
- AC1: a `Storage` implementation backed by S3/GCS, selectable by config; local stays the default.

### PR2-2 — Backups & retention · `todo`
- AC1: documented DB + asset backup; render/asset retention policy + cleanup job.

### PR2-3 — GPU topology + pinned ComfyUI · `todo`
- AC1: documented GPU deployment; pinned ComfyUI + custom-node versions; readiness-gated model servers.

### PR2-4 — Security headers + scans · `todo`
- AC1: CSP/HSTS/X-Frame-Options at the proxy; path-traversal test for uploads; isolation pen-test checklist.

### PR2-5 — Performance · `todo`
- AC1: optimize queue-position query; catalog caching; add indexes as needed.

### PR2-6 — Product/legal · `todo`
- AC1: content-moderation hook on generated outputs; model-licensing notes; ToS/privacy/GDPR.

### PR2-7 — Runbook · `todo`
- AC1: deploy runbook, env-var reference, scaling guide, restore-from-backup drill.

---

## Suggested order (first deployable slice)
PR0-1 ✅ → PR0-2 → PR0-3 → PR0-4 → PR0-5 → PR0-6 → PR0-7 → PR0-8 → PR0-9,
then P1, then P2.
