"""In-process sliding-window rate limiting for sensitive endpoints.

This protects a single API instance. Account lockout (stored in the database) is the
cross-instance defence; move these counters to a shared store if the API is scaled out
horizontally and per-IP limits must be global.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_registry: list["RateLimiter"] = []


class RateLimiter:
    def __init__(self, name: str, limit: int, window_seconds: int = 60) -> None:
        self.name = name
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        _registry.append(self)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def __call__(self, request: Request) -> None:
        """FastAPI dependency: limit by client IP."""
        client_ip = request.client.host if request.client else "unknown"
        if not self.allow(client_ip):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many requests. Please wait a minute and try again.",
            )


def reset_all_rate_limits() -> None:
    for limiter in _registry:
        limiter.reset()
