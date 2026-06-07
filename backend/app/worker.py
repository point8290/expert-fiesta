"""PR0-5 — Background job worker.

A single worker claims queued ``Job`` rows oldest-first and runs the registered
handler for each, which serializes GPU work without extra infrastructure. Run it
as a separate process:

    python -m app.worker

Generation endpoints enqueue jobs when ``ASYNC_JOBS=true``; otherwise they run
inline (the default, used in tests and simple local dev).
"""
import logging
import time
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import SessionLocal
from .models import Job, Project, Scene
from .services.clips import generate_clip_for_scene, resolve_backend
from .services.jobs import ProgressFn, run_job
from .storage import Storage
from .video.registry import build_registry

logger = logging.getLogger("lmvs.worker")

JobHandler = Callable[[Session, Job, ProgressFn], Optional[str]]


def _handle_clip(db: Session, job: Job, progress: ProgressFn) -> Optional[str]:
    scene = db.get(Scene, job.scene_id)
    project = db.get(Project, scene.project_id)
    backend = resolve_backend(build_registry(), project, scene)
    progress(0.1)
    return generate_clip_for_scene(db, scene, backend, Storage(get_settings().storage_dir))


JOB_HANDLERS: dict[str, JobHandler] = {"clip": _handle_clip}


def claim_next_job(db: Session) -> Job | None:
    """The oldest queued job (FIFO). Single-worker, so no locking needed."""
    return db.scalars(
        select(Job).where(Job.status == "queued").order_by(Job.created_at.asc())
    ).first()


def process_one(db: Session, handlers: dict[str, JobHandler] | None = None) -> bool:
    """Run the next queued job. Returns False if the queue is empty."""
    handlers = handlers if handlers is not None else JOB_HANDLERS
    job = claim_next_job(db)
    if job is None:
        return False
    handler = handlers.get(job.type)
    if handler is None:
        job.status = "failed"
        job.error = f"No handler for job type: {job.type}"
        db.commit()
        return True
    run_job(db, job, lambda progress: handler(db, job, progress))
    return True


def run_forever(poll_seconds: float = 1.0) -> None:  # pragma: no cover - loop
    logger.info("Job worker started")
    while True:
        db = SessionLocal()
        try:
            ran = process_one(db)
        except Exception:  # noqa: BLE001 - keep the worker alive
            logger.exception("Worker iteration failed")
            ran = False
        finally:
            db.close()
        if not ran:
            time.sleep(poll_seconds)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    run_forever()
