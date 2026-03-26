"""Issue attachment repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import IssueAttachment


class IssueAttachmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_issue(self, issue_id: str) -> list[IssueAttachment]:
        q = select(IssueAttachment).where(IssueAttachment.issue_id == issue_id).order_by(IssueAttachment.created_at.desc())
        result = await self.db.execute(q)
        return list(result.scalars().all())
