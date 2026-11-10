"""A small, dependency-free sliding-window rate limiter.

The limiter is process-local.  It is intended to blunt credential-stuffing and
enumeration attempts against the authentication endpoints; it is not a
distributed quota system.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from core.errors import RateLimitError


class SlidingWindowRateLimiter:
    """Track request timestamps per key and reject when the limit is exceeded."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        """Raise `RateLimitError` when `key` has exceeded `limit` hits."""
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                raise RateLimitError(
                    "Too many attempts. Please wait before trying again.",
                    retry_after=retry_after,
                )

            bucket.append(now)
            self._prune(cutoff)

    def reset(self, key: str) -> None:
        """Clear the counters for a key (called after a successful login)."""
        with self._lock:
            self._hits.pop(key, None)

    def _prune(self, cutoff: float) -> None:
        empty = [key for key, bucket in self._hits.items() if not bucket or bucket[-1] <= cutoff]
        for key in empty:
            self._hits.pop(key, None)


rate_limiter = SlidingWindowRateLimiter()
