"""Singleton async Redis client."""
import logging

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get or create Redis client (lazy init)."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        logger.info(f"Redis connected: {settings.redis_url}")
    return _redis


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis
    if _redis is not None:
        try:
            await _redis.aclose()
        except RuntimeError:
            pass  # Event loop already closed
        _redis = None
        logger.info("Redis connection closed")


async def ping() -> bool:
    """Redis healthcheck."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return False
