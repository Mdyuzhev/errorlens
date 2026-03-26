"""WorkLog repository - data access layer."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import WorkLog
from app.repositories.base import BaseRepository


class WorkLogRepository(BaseRepository[WorkLog]):
    """Repository for WorkLog CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(WorkLog, db)

    async def list_by_issue(self, issue_id: str) -> list[WorkLog]:
        """List work logs for a task, newest first."""
        stmt = (
            select(WorkLog)
            .where(WorkLog.issue_id == issue_id)
            .order_by(WorkLog.log_date.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_hours(self, issue_id: str) -> float:
        """Get total logged hours for a task."""
        stmt = select(func.sum(WorkLog.hours)).where(WorkLog.issue_id == issue_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0.0
