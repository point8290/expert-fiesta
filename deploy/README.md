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
