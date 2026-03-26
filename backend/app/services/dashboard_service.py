import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.task import Task, TaskType, Component
from app.models.user import User
from app.services.redis_client import get_redis

logger = logging.getLogger(__name__)

DASHBOARD_CACHE_TTL = 300
CACHE_KEY_PREFIX = "dashboard"


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stats(self, project_id: str) -> tuple[dict, bool]:
        """Return (data, cache_hit)."""
        # Try Redis cache first
        try:
            redis = await get_redis()
            cache_key = f"{CACHE_KEY_PREFIX}:{project_id}"
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached), True
        except Exception:
            logger.warning("Redis unavailable for dashboard cache, computing without cache")
            redis = None
            cache_key = None

        data = await self._compute_stats(project_id)

        # Write to cache if Redis available
        if redis and cache_key:
            try:
                await redis.setex(cache_key, DASHBOARD_CACHE_TTL, json.dumps(data))
            except Exception:
                logger.warning("Failed to write dashboard cache to Redis")

        return data, False

    async def _compute_stats(self, project_id: str) -> dict:
        # by_type
        result = await self.db.execute(
            select(TaskType.name, TaskType.color, func.count(Task.id).label("count"))
            .join(Task, Task.type_id == TaskType.id, isouter=True)
            .where(Task.project_id == project_id)
            .group_by(TaskType.id, TaskType.name, TaskType.color)
        )
        by_type = [{"name": r.name, "color": r.color, "count": r.count} for r in result.all()]

        # by_priority
        result = await self.db.execute(
            select(Task.priority, func.count(Task.id).label("count"))
            .where(Task.project_id == project_id)
            .group_by(Task.priority)
        )
        by_priority = [{"priority": r.priority, "count": r.count} for r in result.all()]

        # by_component
        result = await self.db.execute(
            select(Component.name, func.count(Task.id).label("count"))
            .join(Task, Task.component_id == Component.id, isouter=True)
            .where(Component.project_id == project_id)
            .group_by(Component.id, Component.name)
        )
        by_component = [{"component": r.name, "count": r.count} for r in result.all()]

        # top_assignees
        result = await self.db.execute(
            select(User.username, User.display_name, func.count(Task.id).label("closed"))
            .join(Task, Task.assignee_id == User.id)
            .where(Task.project_id == project_id, Task.status == "done")
            .group_by(User.id, User.username, User.display_name)
            .order_by(func.count(Task.id).desc())
            .limit(5)
        )
        top_assignees = [{"username": r.username, "display_name": r.display_name, "closed": r.closed} for r in result.all()]

        return {
            "by_type": by_type,
            "by_priority": by_priority,
            "by_component": by_component,
            "top_assignees": top_assignees,
        }
