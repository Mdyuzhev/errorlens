"""IssueAttachment repository - data access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import IssueAttachment
from app.repositories.base import BaseRepository


class IssueAttachmentRepository(BaseRepository[IssueAttachment]):
    """Repository for IssueAttachment CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(IssueAttachment, db)

    async def list_by_issue(self, issue_id: str) -> list[IssueAttachment]:
        """List attachments for a task, newest first."""
        stmt = (
            select(IssueAttachment)
            .where(IssueAttachment.issue_id == issue_id)
            .order_by(IssueAttachment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_object_key(self, object_key: str) -> IssueAttachment | None:
        """Get attachment by unique S3 object key."""
        return await self.get_by_field("object_key", object_key)
