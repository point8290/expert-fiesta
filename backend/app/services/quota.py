"""PR1-5 — Per-user quotas. Reads the same Job/Project rows usage is metered from."""
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Job, Project, User

ACTIVE_STATUSES = ("queued", "running")


def assert_project_quota(db: Session, user: User) -> None:
    cap = get_settings().max_projects_per_user
    count = db.scalar(
        select(func.count()).select_from(Project).where(Project.owner_id == user.id)
    )
    if count >= cap:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Project limit reached ({cap})",
        )


def assert_active_job_quota(db: Session, user: User) -> None:
    cap = get_settings().max_active_jobs_per_user
    count = db.scalar(
        select(func.count())
        .select_from(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Project.owner_id == user.id, Job.status.in_(ACTIVE_STATUSES))
    )
    if count >= cap:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Active generation-job limit reached ({cap})",
        )


def assert_gpu_budget(db: Session, user: User) -> None:
    cap = get_settings().max_gpu_seconds_per_user
    if cap <= 0:  # 0 = unlimited
        return
    used = db.scalar(
        select(func.coalesce(func.sum(Job.gpu_seconds), 0.0))
        .select_from(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Project.owner_id == user.id)
    )
    if used >= cap:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GPU budget exhausted ({used:.0f}s / {cap:.0f}s)",
        )
