"""P2-S6 — Job queue.

A ``Job`` row tracks each slow generation task's status, progress, and errors so
the UI can show queue position and live progress. Tasks are plain callables that
receive a ``progress`` callback; ``run_job`` drives the lifecycle and captures
failures. A single worker processes jobs in order, which also serializes GPU use.
"""
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..models import Job

# A task does the work and returns an optional result path (e.g. the clip file).
ProgressFn = Callable[[float], None]
JobTask = Callable[[ProgressFn], Optional[str]]


def create_job(
    db: Session,
    job_type: str,
    project_id: str,
    scene_id: str | None = None,
    target_id: str | None = None,
) -> Job:
    job = Job(
        type=job_type,
        project_id=project_id,
        scene_id=scene_id,
        target_id=target_id,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_job(db: Session, job: Job, task: JobTask) -> Job:
    """Execute a task, recording running/succeeded/failed and progress."""
    job.status = "running"
    db.commit()

    def progress(value: float) -> None:
        job.progress = max(0.0, min(1.0, value))
        db.commit()

    try:
        result = task(progress)
        job.status = "succeeded"
        job.result_path = result
        job.progress = 1.0
    except Exception as exc:  # noqa: BLE001 - failures are recorded, not raised
        job.status = "failed"
        job.error = str(exc)
    db.commit()
    db.refresh(job)
    return job


def execute_job(
    db: Session,
    job_type: str,
    project_id: str,
    task: JobTask,
    scene_id: str | None = None,
) -> Job:
    """Create a job and run it. (MVP runs inline; the Job row still gives the UI
    full status/progress/error history.)"""
    job = create_job(db, job_type, project_id, scene_id)
    return run_job(db, job, task)
