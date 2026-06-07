"""PR1-1 — simple in-memory sliding-window rate limiter for auth endpoints.

Single-instance only; back it with Redis for multi-instance deploys.
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from .config import get_settings

_attempts: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request, bucket: str) -> None:
    settings = get_settings()
    window = settings.rate_limit_window_seconds
    client = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client}"
    now = time.monotonic()

    attempts = _attempts[key]
    while attempts and attempts[0] <= now - window:
        attempts.popleft()
    if len(attempts) >= settings.rate_limit_max_attempts:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts — please slow down",
        )
    attempts.append(now)
