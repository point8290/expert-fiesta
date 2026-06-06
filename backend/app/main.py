"""FastAPI application entrypoint for the Local Music Video Studio backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routers import audio, lyrics, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For local-first single-user use; later phases can switch to migrations.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Local Music Video Studio", lifespan=lifespan)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(projects.router)
app.include_router(lyrics.router)
app.include_router(audio.router)
