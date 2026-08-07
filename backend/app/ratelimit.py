"""Rate limiting for a free, publicly-reachable upload endpoint.

Scope, stated plainly: counters live in this process. On a single instance
that is exact. Behind several instances each one enforces its own budget, so
effective limits multiply by instance count — fine as a blunt abuse control,
not a billing mechanism. Swapping in Redis means replacing ``_Window`` only.

Limits are deliberately generous for humans and tight for scripts: a real
applicant runs a handful of checks, a scraper runs hundreds.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from .config import settings


class _Window:
    """Sliding-window counter, keyed by an arbitrary string."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def hit(self, key: str, limit: int, period_s: float) -> tuple[bool, int, float]:
        """Record an event. Returns (allowed, remaining, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            self._maybe_sweep(now)
            events = self._events[key]
            cutoff = now - period_s
            while events and events[0] < cutoff:
                events.popleft()

            if len(events) >= limit:
                retry = max(1.0, events[0] + period_s - now)
                return False, 0, retry

            events.append(now)
            return True, limit - len(events), 0.0

    def peek(self, key: str, limit: int, period_s: float) -> int:
        now = time.monotonic()
        with self._lock:
            events = self._events.get(key)
            if not events:
                return limit
            cutoff = now - period_s
            live = sum(1 for e in events if e >= cutoff)
            return max(0, limit - live)

    def _maybe_sweep(self, now: float) -> None:
        """Drop empty keys occasionally so memory does not grow unbounded."""
        if now - self._last_sweep < 300:
            return
        self._last_sweep = now
        for key in [k for k, v in self._events.items() if not v]:
            del self._events[key]


_window = _Window()

HOUR = 3600.0
DAY = 86400.0


def client_ip(request: Request) -> str:
    """Best-effort client IP, honouring one proxy hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


def _enforce(key: str, limit: int, period: float, message: str) -> None:
    if not settings.rate_limit_enabled:
        return
    allowed, _remaining, retry = _window.hit(key, limit, period)
    if not allowed:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message,
            headers={"Retry-After": str(int(retry))},
        )


# --------------------------------------------------------------------------
# limiters used as FastAPI dependencies
# --------------------------------------------------------------------------


def limit_auth(request: Request) -> None:
    """Throttle registration and login attempts per IP."""
    _enforce(
        f"auth:{client_ip(request)}",
        settings.rate_limit_auth_per_hour_ip,
        HOUR,
        "Too many sign-in attempts from this network. Please wait and try again.",
    )


def limit_upload(request: Request) -> None:
    _enforce(
        f"upload:{client_ip(request)}",
        settings.rate_limit_uploads_per_hour_ip,
        HOUR,
        "Too many uploads from this network. Please wait and try again.",
    )


def limit_check_run(request: Request, user_id: str) -> None:
    """Two ceilings: a per-account daily cap and a per-IP hourly burst cap."""
    _enforce(
        f"run-ip:{client_ip(request)}",
        settings.rate_limit_checks_per_hour_ip,
        HOUR,
        "Too many checks started from this network in the last hour. "
        "Please wait and try again.",
    )
    _enforce(
        f"run-user:{user_id}",
        settings.rate_limit_checks_per_day,
        DAY,
        f"You have reached the limit of {settings.rate_limit_checks_per_day} "
        "checks for today. This limit protects the free service; it resets "
        "in 24 hours.",
    )


def remaining_today(user_id: str) -> int:
    return _window.peek(
        f"run-user:{user_id}", settings.rate_limit_checks_per_day, DAY
    )


def reset() -> None:
    """Clear all counters. For tests."""
    global _window
    _window = _Window()
