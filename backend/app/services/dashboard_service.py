"""Dashboard stats service with Redis cache."""

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "dashboard:stats:"
CACHE_TTL = 300  # 5 minutes


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stats(self, project_id: str) -> tuple[dict, bool]:
        """Return aggregated stats; (data, cache_hit)."""
        from app.services.redis_client import get_redis

        cache_key = f"{CACHE_KEY_PREFIX}{project_id}"
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached), True
        except Exception as e:
            logger.warning(f"Redis cache miss: {e}")

        data = await self._compute(project_id)

        try:
            redis = await get_redis()
            await redis.set(cache_key, json.dumps(data), ex=CACHE_TTL)
        except Exception as e:
            logger.warning(f"Redis cache set failed: {e}")

        return data, False

    async def _compute(self, project_id: str) -> dict:
        q = (
            select(Task.status, func.count(Task.id))
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        )
        result = await self.db.execute(q)
        by_status = {row[0]: row[1] for row in result.all()}

        q2 = (
            select(Task.priority, func.count(Task.id))
            .where(Task.project_id == project_id)
            .group_by(Task.priority)
        )
        result2 = await self.db.execute(q2)
        by_priority = {row[0]: row[1] for row in result2.all()}

        total = sum(by_status.values())
        return {"total": total, "by_status": by_status, "by_priority": by_priority}
