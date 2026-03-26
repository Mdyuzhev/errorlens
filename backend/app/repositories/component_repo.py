"""Repository for project components."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Component
from app.repositories.base import BaseRepository


class ComponentRepository(BaseRepository[Component]):
    """Data access for project components."""

    def __init__(self, session: AsyncSession):
        super().__init__(Component, session)

    async def list_by_project(self, project_id: str) -> list[Component]:
        """List all components for a project, ordered by name."""
        query = (
            select(Component)
            .where(Component.project_id == project_id)
            .order_by(Component.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, name: str, project_id: str) -> Component | None:
        """Get component by name within a project (uniqueness check)."""
        query = select(Component).where(
            Component.project_id == project_id,
            Component.name == name,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
