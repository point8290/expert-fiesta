"""FastAPI application entrypoint for the Local Music Video Studio backend."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import assert_production_ready, get_settings
from .database import Base, engine
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
    # For local-first single-user use; later phases can switch to migrations.
    Base.metadata.create_all(bind=engine)
    # P2-S1 AC3: validate committed ComfyUI workflows load on startup.
    try:
        from .comfyui.client import ComfyUIClient

        ComfyUIClient().smoke_test()
    except Exception as exc:  # pragma: no cover - never block startup
        logging.getLogger("uvicorn.error").warning(
            "ComfyUI workflow smoke-test failed: %s", exc
        )
    yield


app = FastAPI(title="Local Music Video Studio", lifespan=lifespan)

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
    return {"status": "ok"}


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
