"""CB-4 — video backend fallback + circuit breaker.

Wraps a primary `VideoBackend` (e.g. RunPod) with a fallback (the managed `cloud`
backend). On primary failure it switches to the fallback; after repeated failures
the circuit opens and traffic skips the primary for a cooldown.
"""
import logging
import time

logger = logging.getLogger("lmvs.video.fallback")


class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown: float = 60.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = 0
        self.open_until = 0.0

    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = time.monotonic() + self.cooldown
            self.failures = 0


# Process-wide breaker shared across requests/worker iterations.
_default_breaker = CircuitBreaker()


class FallbackVideoBackend:
    """Implements ``VideoBackend`` by delegating to primary, falling back on error."""

    def __init__(self, primary, fallback, breaker: CircuitBreaker | None = None):
        self.primary = primary
        self.fallback = fallback
        self.workflow = getattr(primary, "workflow", "fallback")
        self.breaker = breaker if breaker is not None else _default_breaker

    def generate(self, *args, **kwargs) -> str:
        if self.breaker.is_open():
            logger.warning("video circuit open — using fallback backend")
            return self.fallback.generate(*args, **kwargs)
        try:
            result = self.primary.generate(*args, **kwargs)
            self.breaker.record_success()
            return result
        except Exception as exc:  # noqa: BLE001 - any primary failure → fallback
            self.breaker.record_failure()
            logger.warning("primary video backend failed (%s) — using fallback", exc)
            return self.fallback.generate(*args, **kwargs)
