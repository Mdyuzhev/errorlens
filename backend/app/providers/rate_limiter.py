"""Rate limiter for LLM API calls."""

import asyncio
import time
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    requests_per_minute: int
    tokens_per_minute: int = 0


PROVIDER_LIMITS = {
    "anthropic": RateLimitConfig(requests_per_minute=50, tokens_per_minute=40000),
    "openai": RateLimitConfig(requests_per_minute=60, tokens_per_minute=90000),
    "gigachat": RateLimitConfig(requests_per_minute=30),
    "groq": RateLimitConfig(requests_per_minute=30, tokens_per_minute=6000),
    "gemini": RateLimitConfig(requests_per_minute=60),
    "ollama": RateLimitConfig(requests_per_minute=1000),
}


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, provider: str):
        config = PROVIDER_LIMITS.get(provider, RateLimitConfig(requests_per_minute=30))
        self.requests_per_minute = config.requests_per_minute
        self.request_timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until rate limit allows a request."""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60
            self.request_timestamps = [ts for ts in self.request_timestamps if ts > minute_ago]

            if len(self.request_timestamps) >= self.requests_per_minute:
                wait_time = self.request_timestamps[0] - minute_ago
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self.request_timestamps.append(time.time())


_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(provider: str) -> RateLimiter:
    """Get or create rate limiter for provider."""
    if provider not in _limiters:
        _limiters[provider] = RateLimiter(provider)
    return _limiters[provider]
