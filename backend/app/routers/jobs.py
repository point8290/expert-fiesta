"""P2-S6 — Job status + queue endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Job, Project
from ..schemas import JobRead, UsageSummary
from ..services.usage import summarize

router = APIRouter(tags=["jobs"])


@router.get("/usage", response_model=UsageSummary)
def global_usage(db: Session = Depends(get_db)):
    return summarize(list(db.scalars(select(Job))))


@router.get("/projects/{project_id}/usage", response_model=UsageSummary)
def project_usage(project_id: str, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    jobs = list(db.scalars(select(Job).where(Job.project_id == project_id)))
    return summarize(jobs)


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _with_position(db, job)


@router.get("/projects/{project_id}/jobs", response_model=list[JobRead])
def list_jobs(project_id: str, db: Session = Depends(get_db)):
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    jobs = list(
        db.scalars(
            select(Job)
            .where(Job.project_id == project_id)
            .order_by(Job.created_at.desc())
        )
    )
    return [_with_position(db, job) for job in jobs]


def _queue_order(db: Session) -> list[str]:
    """Ids of all queued jobs across projects, oldest first (FIFO worker order)."""
    return list(
        db.scalars(
            select(Job.id).where(Job.status == "queued").order_by(Job.created_at.asc())
        )
    )


def _with_position(db: Session, job: Job) -> JobRead:
    read = JobRead.model_validate(job)
    if job.status == "queued":
        order = _queue_order(db)
        read.queue_position = order.index(job.id) + 1
    return read
