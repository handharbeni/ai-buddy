"""Rate limiter using token bucket algorithm for per-user, per-IP, and per-tool limiting."""

import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = 0
    last_refill: float = field(default_factory=time.time)

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class TokenBucketRateLimiter:
    """Rate limiter using token buckets for multiple dimensions."""

    def __init__(
        self,
        default_capacity: int = 60,
        default_refill_rate: float = 1.0,  # 1 token per second = 60 per minute
    ):
        self.default_capacity = default_capacity
        self.default_refill_rate = default_refill_rate
        self._buckets: Dict[str, TokenBucket] = {}

    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create a token bucket for the given key."""
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                capacity=self.default_capacity,
                refill_rate=self.default_refill_rate,
            )
        return self._buckets[key]

    def check_rate_limit(
        self,
        identifier: str,
        dimension: str = "user",
        tokens: int = 1,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if a request is within rate limits.

        Args:
            identifier: User ID, IP address, or tool name
            dimension: Rate limit dimension (user, ip, tool)
            tokens: Number of tokens to consume

        Returns:
            Tuple of (allowed, metadata)
        """
        key = f"{dimension}:{identifier}"
        bucket = self._get_bucket(key)
        allowed = bucket.consume(tokens)

        return allowed, {
            "dimension": dimension,
            "identifier": identifier,
            "tokens_remaining": round(bucket.tokens, 2),
            "capacity": bucket.capacity,
            "refill_rate": bucket.refill_rate,
        }

    def get_rate_limit_status(self, identifier: str, dimension: str = "user") -> Dict[str, Any]:
        """Get current rate limit status without consuming tokens."""
        key = f"{dimension}:{identifier}"
        bucket = self._get_bucket(key)
        bucket._refill()

        return {
            "dimension": dimension,
            "identifier": identifier,
            "tokens_remaining": round(bucket.tokens, 2),
            "capacity": bucket.capacity,
            "refill_rate": bucket.refill_rate,
        }

    def cleanup_stale_buckets(self, max_idle_seconds: int = 3600) -> int:
        """Remove buckets that haven't been used recently."""
        now = time.time()
        stale_keys = [
            key for key, bucket in self._buckets.items()
            if now - bucket.last_refill > max_idle_seconds
        ]
        for key in stale_keys:
            del self._buckets[key]
        return len(stale_keys)