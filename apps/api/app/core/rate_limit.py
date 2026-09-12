"""Rate limiting utility supporting in-memory and Redis backends."""
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request
from app.core.errors import RateLimitExceededError


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter."""

    def __init__(self):
        self._records: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        
        # Clean older requests
        timestamps = [t for t in self._records[key] if t > cutoff]
        if len(timestamps) >= max_requests:
            self._records[key] = timestamps
            return False
        
        timestamps.append(now)
        self._records[key] = timestamps
        return True


rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(key: str, max_requests: int, window_seconds: int = 60):
    """Raise RateLimitExceededError if limit breached."""
    if not rate_limiter.check_rate_limit(key, max_requests, window_seconds):
        raise RateLimitExceededError(
            f"Rate limit of {max_requests} requests per {window_seconds}s exceeded."
        )
