from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request


DEFAULT_RATE_LIMIT_PER_MINUTE = 10


class RateLimitExceeded(Exception):
    pass


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True

        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True


def int_from_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(request: Request) -> None:
    limit = int_from_env("RATE_LIMIT_PER_MINUTE", DEFAULT_RATE_LIMIT_PER_MINUTE)
    if not rate_limiter.allow(client_ip(request), limit):
        raise RateLimitExceeded("Too many requests. Please slow down and try again.")


rate_limiter = InMemoryRateLimiter()

# Future hook: replace rate_limiter with Redis/token-bucket storage for multi-instance deployments.
