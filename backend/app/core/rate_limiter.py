"""
Rate limiter with exponential backoff for auth endpoints.

⚠️  SECURITY LIMITATION — IN-MEMORY STORE, SINGLE-WORKER ONLY
   This implementation stores state in process memory.  With multiple uvicorn
   workers each process maintains its own counter, so an attacker can multiply
   the effective limit by the number of workers.  The docker-compose deployment
   is pinned to --workers 1 as a mitigation.
   Production fix: replace _state with a Redis-backed store using slowapi +
   redis.asyncio and restore --workers to the desired concurrency level.

Limits:
  - 5 attempts per IP per 60 s on auth endpoints
  - Exponential backoff on excess: blocked for min(2^violations, 3600) seconds
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status


@dataclass
class _Window:
    timestamps: deque = field(default_factory=deque)
    blocked_until: float = 0.0
    violation_count: int = 0


class RateLimiter:
    """
    Sliding-window rate limiter with exponential backoff per key.
    Safe for single-process async usage; not designed for multi-worker deployments.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self._max = max_requests
        self._window = window_seconds
        self._state: dict[str, _Window] = defaultdict(_Window)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        """Raise HTTP 429 if key has exceeded the limit."""
        async with self._lock:
            win = self._state[key]
            now = time.monotonic()

            if win.blocked_until > now:
                remaining = int(win.blocked_until - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Try again in {remaining} seconds.",
                    headers={"Retry-After": str(remaining)},
                )

            cutoff = now - self._window
            while win.timestamps and win.timestamps[0] < cutoff:
                win.timestamps.popleft()

            if len(win.timestamps) >= self._max:
                win.violation_count += 1
                backoff = min(2 ** win.violation_count, 3600)
                win.blocked_until = now + backoff
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Try again in {backoff} seconds.",
                    headers={"Retry-After": str(backoff)},
                )

            win.timestamps.append(now)

    def reset(self, key: str) -> None:
        """Reset counters after a successful operation."""
        self._state.pop(key, None)


# Shared instances — one per logical limit group
auth_limiter = RateLimiter(max_requests=5, window_seconds=60)
public_scan_limiter = RateLimiter(max_requests=10, window_seconds=3600)
