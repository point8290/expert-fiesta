# Production Readiness Checklist

The product is **feature-complete** (Phases 1–5 + auth) and CI-green, but it was
built local-first with mocked adapters. This is the gap list to make it safe to
deploy and operate for real users, grounded in the current code.

Priority: **P0** = blocker (don't deploy without it) · **P1** = important (soon
after launch) · **P2** = hardening / scale.

---

## P0 — Blockers

### Data & migrations
- [ ] **Move off SQLite to PostgreSQL.** `app/database.py` defaults to SQLite and
      `app/main.py` calls `Base.metadata.create_all` on startup. SQLite can't
      handle concurrent writers or multiple web workers.
- [ ] **Add Alembic migrations.** Replace `create_all` with versioned migrations;
      run them as a deploy step, not at app startup. Note `Project.owner_id` is
      currently `nullable=True` for test convenience — tighten to `NOT NULL` via a
      migration once seeded.

### Secrets & config
- [ ] **Set `AUTH_SECRET` from a secret manager.** `app/services/auth.py` ships a
      dev default; a known JWT signing key = full account takeover. Fail startup
      if it's unset in production.
- [ ] **Centralize config** (pydantic `BaseSettings`): `DATABASE_URL`,
      `AUTH_SECRET`, `OLLAMA_HOST`, `COMFYUI_HOST`, `STORAGE_DIR`,
      `CLOUD_VIDEO_URL`/`CLOUD_VIDEO_API_KEY`, `ACESTEP_MODEL`, CORS origins.
      Validate required vars at boot.

### Async job execution (correctness, not just scale)
- [ ] **Run generation off the request thread.** `execute_job` (`services/jobs.py`)
      runs **inline/synchronously**, so a clip/keyframe request blocks the HTTP
      worker for minutes and ties up a connection. Introduce a real worker
      (RQ/Celery + Redis, or an in-process background worker with a DB-backed
      queue) and a **single GPU worker** to serialize model calls.

### Serving generated assets
- [ ] **Add media endpoints.** The API returns filesystem paths
      (`clipPath`, `keyframePath`, render `outputPath`) but there's **no way to
      fetch the bytes** over HTTP. Add authenticated download/stream endpoints
      (or signed URLs) for keyframes, clips, references, and the final MP4.

### CORS & frontend build
- [ ] **Add `CORSMiddleware`.** None is configured; the browser app on a
      different origin will be blocked. Allow only the known frontend origin(s).
- [ ] **Build the frontend for production.** `frontend/Dockerfile` runs
      `npm run dev`. Switch to `next build && next start` (or static export behind
      a CDN) and bake `NEXT_PUBLIC_API_URL` at build time per environment.

### TLS / edge
- [ ] **Terminate TLS** at a reverse proxy (Caddy/nginx/Traefik); redirect HTTP→HTTPS.
- [ ] **Bound upload sizes.** Audio/video/image uploads have type checks but no
      size limit — cap them at the proxy and in FastAPI to avoid disk-fill / DoS.

---

## P1 — Important

### Auth hardening
- [ ] Rate-limit `POST /auth/login` and `/auth/register` (brute-force / abuse).
- [ ] Token lifecycle: short-lived access + refresh tokens, or server-side
      session/revocation; today tokens are 24h with no logout-side invalidation.
- [ ] Frontend: intercept **401 responses** (expired token mid-session) → clear
      token + redirect to `/login`. `RequireAuth` only checks token *presence*.
- [ ] Stronger password policy + (optional) email verification.

### Observability
- [ ] Structured JSON logging with request IDs; log generation job lifecycle.
- [ ] Error tracking (Sentry or similar) on backend and frontend.
- [ ] `/health` exists (liveness); add a **readiness** probe that checks DB and
      (optionally) Ollama/ComfyUI reachability.
- [ ] Basic metrics (request latency, job durations, queue depth, GPU utilization).

### Quotas & cost control
- [ ] Enforce **per-user quotas** on expensive generation. Usage is *metered*
      (`/usage`) but not *enforced*; GPU/cloud spend is unbounded today.
- [ ] Wire the cloud fallback's API key + budget guardrails (`CloudVideoBackend`).

### Pagination & query limits
- [ ] Add pagination to `GET /projects`, `/scenes`, `/projects/{id}/jobs` — all
      return unbounded lists. Add a `LIMIT` and cursor/offset.

### CI/CD
- [ ] Publish versioned images (GHCR) on tag/merge; today CI only *builds* them.
- [ ] Add a deploy pipeline that runs migrations then rolls out.
- [ ] Dependency + secret scanning (Dependabot, `pip-audit`, `npm audit`, gitleaks).

### Real-path test coverage
- [ ] Adapters are mocked in all 139 backend tests. Add **integration smoke tests**
      against the real boundaries: an FFmpeg render with actual clips, a librosa
      analysis, and a ComfyUI/Ollama happy-path (behind a marker/opt-in).

---

## P2 — Hardening & scale

### Storage & data lifecycle
- [ ] Move assets to **object storage** (S3/GCS) for multi-instance + durability;
      `Storage` currently writes to a local dir.
- [ ] Backups + retention for DB and assets; lifecycle/cleanup of old renders.
- [ ] Soft-delete + cascade review for projects.

### Model / GPU infrastructure
- [ ] Document hardware requirements and topology: GPU hosts for ComfyUI
      (image/video) and Ollama (LLM); pin ComfyUI + custom-node versions (the
      build plan flagged node breakage as the top risk).
- [ ] Autoscale or queue GPU workers; backpressure when the queue is deep.
- [ ] Health-gate model servers in the readiness probe.

### Security
- [ ] Security headers (CSP, HSTS, X-Frame-Options) at the proxy.
- [ ] Verify no path traversal in uploads (`Storage.save_upload` uses
      `Path(filename).name` — keep it; add tests).
- [ ] Pen-test the multi-tenant isolation boundary end to end.

### Performance
- [ ] Optimize queue-position computation (currently re-scans queued jobs per job).
- [ ] Add DB indexes as access patterns emerge (owner_id / project_id are indexed).
- [ ] Cache template/preset catalog responses.

### Product / legal
- [ ] Content moderation pass on generated outputs (beyond the originality prompts).
- [ ] Model licensing review (LTX-Video, Wan 2.2, HunyuanVideo, ACE-Step) and a
      stance on generated-content ownership.
- [ ] ToS, privacy policy, and GDPR handling for user accounts/email.

### Docs / runbook
- [ ] Deployment runbook, env-var reference, scaling guide, incident playbook.
- [ ] Restore-from-backup drill.

---

## Suggested first slice (a realistic "make it deployable" milestone)

1. Postgres + Alembic; `create_all` removed.
2. pydantic Settings + required-secret validation (`AUTH_SECRET`).
3. Background worker + single GPU worker for generation jobs.
4. Authenticated media-download endpoints (or signed URLs).
5. `CORSMiddleware` + production frontend build.
6. Reverse proxy with TLS + upload size limits.
7. Structured logging + Sentry + readiness probe.
8. Publish images in CI; deploy job runs migrations.

That set turns the current feature-complete app into something you can safely put
in front of real users; the P1/P2 items follow as it grows.
