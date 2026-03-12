"""Redis cache service for hot data (task types, statuses, transitions)."""

import json
import logging
from typing import Any, Awaitable, Callable

from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)


async def get_or_set(
    key: str,
    fetcher: Callable[[], Awaitable[Any]],
    ttl: int = 300,
) -> Any:
    """Get from Redis cache or fetch and store."""
    try:
        r = await get_redis()
        cached = await r.get(key)
        if cached:
            logger.debug(f"[cache] HIT {key}")
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"[cache] Redis read error: {e}")

    result = await fetcher()

    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(result, default=str))
        logger.debug(f"[cache] SET {key} ttl={ttl}")
    except Exception as e:
        logger.warning(f"[cache] Redis write error: {e}")

    return result


async def invalidate(key: str) -> None:
    """Delete a single cache key."""
    try:
        r = await get_redis()
        await r.delete(key)
        logger.debug(f"[cache] INVALIDATE {key}")
    except Exception as e:
        logger.warning(f"[cache] Redis delete error: {e}")


async def invalidate_prefix(prefix: str) -> None:
    """Delete all keys matching prefix*."""
    try:
        r = await get_redis()
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor, match=f"{prefix}*", count=100)
            if keys:
                await r.delete(*keys)
                logger.debug(f"[cache] INVALIDATE PREFIX {prefix} ({len(keys)} keys)")
            if cursor == 0:
                break
    except Exception as e:
        logger.warning(f"[cache] Redis prefix delete error: {e}")
