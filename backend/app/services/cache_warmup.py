"""Warm up Redis cache on startup for hot data."""

import logging

from app.database import async_session_maker
from app.repositories.task_type_repo import TaskTypeRepository
from app.services import cache_service

logger = logging.getLogger(__name__)


async def warm_up_cache() -> None:
    """Pre-fill cache with task types for all projects."""
    from sqlalchemy import select

    from app.models.db_models import Project

    async with async_session_maker() as db:
        result = await db.execute(select(Project.id))
        project_ids = [row[0] for row in result.all()]

    for pid in project_ids:
        async with async_session_maker() as db:
            repo = TaskTypeRepository(db)
            types = await repo.get_types(pid)
            type_dicts = [_type_to_dict(t) for t in types]
            await cache_service.get_or_set(
                f"task_types:{pid}", _make_fetcher(type_dicts), ttl=300,
            )

    logger.info(f"Cache warmed: {len(project_ids)} projects")


def _make_fetcher(data):
    async def _f():
        return data
    return _f


def _type_to_dict(t) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "name": t.name,
        "slug": t.slug,
        "icon": t.icon,
        "color": t.color,
        "sort_order": t.sort_order,
        "is_active": t.is_active,
        "statuses": [
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug,
                "color": s.color,
                "sort_order": s.sort_order,
                "is_initial": s.is_initial,
                "is_final": s.is_final,
            }
            for s in (t.statuses or [])
        ],
    }
