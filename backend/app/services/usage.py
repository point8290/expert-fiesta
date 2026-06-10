"""P5-S5 — Usage metering.

Aggregates the job queue into a usage summary (counts by type and status) that a
billing layer could meter against later.
"""
from collections import Counter

from ..config import get_settings
from ..models import Job
from ..schemas import UsageSummary


def summarize(jobs: list[Job]) -> UsageSummary:
    by_type: Counter[str] = Counter(job.type for job in jobs)
    total_gpu_seconds = sum(j.gpu_seconds or 0.0 for j in jobs)
    return UsageSummary(
        total_jobs=len(jobs),
        succeeded=sum(1 for j in jobs if j.status == "succeeded"),
        failed=sum(1 for j in jobs if j.status == "failed"),
        by_type=dict(by_type),
        total_gpu_seconds=total_gpu_seconds,
        estimated_cost=total_gpu_seconds * get_settings().gpu_cost_per_second,
    )
