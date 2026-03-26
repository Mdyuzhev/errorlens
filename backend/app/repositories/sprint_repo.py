"""Sprint and SprintIssue repositories."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Sprint, SprintIssue
from app.repositories.base import BaseRepository


class SprintRepository(BaseRepository[Sprint]):
    def __init__(self, db: AsyncSession):
        super().__init__(Sprint, db)

    async def list_by_project(
        self, project_id: str, status: str | None = None
    ) -> list[Sprint]:
        q = select(Sprint).where(Sprint.project_id == project_id)
        if status:
            q = q.where(Sprint.status == status)
        q = q.order_by(Sprint.created_at.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_active_sprint(self, project_id: str) -> Sprint | None:
        q = select(Sprint).where(
            Sprint.project_id == project_id, Sprint.status == "active"
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()


class SprintIssueRepository(BaseRepository[SprintIssue]):
    def __init__(self, db: AsyncSession):
        super().__init__(SprintIssue, db)

    async def list_by_sprint(self, sprint_id: str) -> list[SprintIssue]:
        q = (
            select(SprintIssue)
            .where(SprintIssue.sprint_id == sprint_id)
            .order_by(SprintIssue.rank.asc())
        )
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_sprint_and_issue(
        self, sprint_id: str, issue_id: str
    ) -> SprintIssue | None:
        q = select(SprintIssue).where(
            SprintIssue.sprint_id == sprint_id, SprintIssue.issue_id == issue_id
        )
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def remove_all_for_sprint(self, sprint_id: str) -> int:
        q = delete(SprintIssue).where(SprintIssue.sprint_id == sprint_id)
        result = await self.session.execute(q)
        return result.rowcount
