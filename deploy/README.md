# Deploy notes

## TLS / reverse proxy
[`Caddyfile`](./Caddyfile) is a sample edge config: automatic HTTPS, frontend at
`/`, API under `/api` (prefix stripped). For a containerized deploy, add a
`caddy` service that mounts this file and depends on `backend` + `frontend`.

When fronting the API at `/api`:
- build the frontend image with `--build-arg NEXT_PUBLIC_API_URL=https://YOUR_HOST/api`
- set `CORS_ORIGINS=https://YOUR_HOST` on the backend
- set `AUTH_SECRET` to a strong random value and `ENV=production` (the API
  refuses to boot otherwise)

## Database
Use Postgres in production: `DATABASE_URL=postgresql+psycopg://user:pw@host:5432/lmvs`.
The backend image runs `alembic upgrade head` on start.

## Jobs
Set `ASYNC_JOBS=true` and run the `worker` service so generation runs off the
request path (see `docker-compose.yml`).

## Observability (opt-in)
- Backend: set `SENTRY_DSN` to enable error tracking.
- Frontend: set `NEXT_PUBLIC_SENTRY_DSN` (add `@sentry/nextjs` for full tracing).
- Every API response carries an `X-Request-ID` (logged as JSON) for correlation.

## Releases
Tag `vX.Y.Z` to build + push images to GHCR (`.github/workflows/release.yml`),
then run `alembic upgrade head` and roll out. CI also runs dependency + secret scans.

## LLM provider (CB-1)
Default is local Ollama. For the hosted tier, set:
- `LLM_PROVIDER=anthropic` (or `openai`), `LLM_API_KEY=...`
- optional `LLM_MODEL` (defaults: `claude-sonnet-4-6` / `gpt-4o-mini`), `LLM_BASE_URL`

Transport/availability errors surface as a clean 502 with a helpful message.
