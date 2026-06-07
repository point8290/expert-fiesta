"""FastAPI application entrypoint for the Local Music Video Studio backend."""
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import assert_production_ready, get_settings
from .database import get_db
from .observability import request_id_var, setup_logging
from .routers import (
    audio,
    auth,
    catalog,
    characters,
    jobs,
    lyrics,
    projects,
    render,
    scenes,
    storyboard,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse to boot insecurely in production (e.g. default AUTH_SECRET).
    assert_production_ready(get_settings())
    # Schema is managed by Alembic — run `alembic upgrade head` before starting.
    # P2-S1 AC3: validate committed ComfyUI workflows load on startup.
    try:
        from .comfyui.client import ComfyUIClient

        ComfyUIClient().smoke_test()
    except Exception as exc:  # pragma: no cover - never block startup
        logging.getLogger("uvicorn.error").warning(
            "ComfyUI workflow smoke-test failed: %s", exc
        )
    yield


setup_logging()
app = FastAPI(title="Local Music Video Studio", lifespan=lifespan)
_request_log = logging.getLogger("lmvs.request")


@app.middleware("http")
async def request_context(request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    token = request_id_var.set(rid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        _request_log.info(
            "%s %s -> %s", request.method, request.url.path, response.status_code
        )
        return response
    finally:
        request_id_var.reset(token)

# Allow the browser frontend to call the API cross-origin (configurable via
# CORS_ORIGINS; defaults to the local dev UI).
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health():
    """Liveness — the process is up. No dependencies checked."""
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)):
    """Readiness — verify the database is reachable before taking traffic."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable"
        ) from exc
    return {"status": "ready", "checks": {"database": "ok"}}


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(lyrics.router)
app.include_router(audio.router)
app.include_router(storyboard.router)
app.include_router(scenes.router)
app.include_router(render.router)
app.include_router(characters.router)
app.include_router(jobs.router)
app.include_router(catalog.router)
