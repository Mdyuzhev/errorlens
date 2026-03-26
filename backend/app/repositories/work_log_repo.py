"""Work log repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import WorkLog


class WorkLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_issue(self, issue_id: str) -> list[WorkLog]:
        q = select(WorkLog).where(WorkLog.issue_id == issue_id).order_by(WorkLog.log_date.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())
