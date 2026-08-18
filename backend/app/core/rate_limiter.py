"""
PrepAI — In-Memory Rate Limiter for Gemini-Calling Endpoints.
Prevents accidental depletion of AI API quotas during testing.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
import logging

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter.
    Default: max_requests requests per window_seconds.
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, key: str = "global_ai_quota") -> None:
        """
        Check if request is allowed.
        Raises HTTPException 429 if rate limit is exceeded.
        """
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds

            # Filter out timestamps outside window
            self._timestamps[key] = [
                t for t in self._timestamps[key] if t > cutoff
            ]

            if len(self._timestamps[key]) >= self.max_requests:
                oldest = self._timestamps[key][0]
                retry_after = int(self.window_seconds - (now - oldest)) + 1
                logger.warning(
                    "[RATE_LIMITER] Key '%s' exceeded limit (%d/%ds). Retry after %ds.",
                    key, self.max_requests, int(self.window_seconds), retry_after
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"AI rate limit exceeded: Maximum {self.max_requests} requests per minute allowed. Please try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            self._timestamps[key].append(now)


# Global instance: 15 requests per 60 seconds (aligned with Gemini free tier)
ai_rate_limiter = InMemoryRateLimiter(max_requests=15, window_seconds=60.0)
