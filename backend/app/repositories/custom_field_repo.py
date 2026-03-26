"""Issue custom field/value repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import IssueCustomValue


class IssueCustomValueRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_values_for_issue(self, issue_id: str) -> list[dict]:
        q = select(IssueCustomValue).where(IssueCustomValue.issue_id == issue_id)
        result = await self.db.execute(q)
        return [
            {"field_id": v.field_id, "value": v.value}
            for v in result.scalars().all()
        ]
