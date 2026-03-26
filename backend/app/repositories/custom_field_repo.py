"""Repository for issue custom fields and values."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import IssueCustomField, IssueCustomValue
from app.repositories.base import BaseRepository


class IssueCustomFieldRepository(BaseRepository[IssueCustomField]):
    """Data access for custom field definitions."""

    def __init__(self, session: AsyncSession):
        super().__init__(IssueCustomField, session)

    async def list_by_project(
        self, project_id: str, task_type_id: str | None = None
    ) -> list[IssueCustomField]:
        """List fields for a project, optionally filtered by task type."""
        query = (
            select(IssueCustomField)
            .where(IssueCustomField.project_id == project_id)
            .order_by(IssueCustomField.sort_order)
        )
        if task_type_id is not None:
            query = query.where(IssueCustomField.task_type_id == task_type_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class IssueCustomValueRepository(BaseRepository[IssueCustomValue]):
    """Data access for custom field values on tasks."""

    def __init__(self, session: AsyncSession):
        super().__init__(IssueCustomValue, session)

    async def get_values_for_issue(self, issue_id: str) -> dict[str, object]:
        """Load all custom values for a task, returned as {field_id: value}."""
        query = select(IssueCustomValue).where(IssueCustomValue.issue_id == issue_id)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return {row.field_id: row.value for row in rows}

    async def set_value(
        self, issue_id: str, field_id: str, value: object
    ) -> IssueCustomValue:
        """Upsert a single custom value for a task."""
        query = select(IssueCustomValue).where(
            IssueCustomValue.issue_id == issue_id,
            IssueCustomValue.field_id == field_id,
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
            await self.session.flush()
            return existing

        return await self.create(
            {"issue_id": issue_id, "field_id": field_id, "value": value}
        )

    async def bulk_set_values(self, issue_id: str, values: dict[str, object]) -> None:
        """Set multiple custom values for a task."""
        for field_id, value in values.items():
            await self.set_value(issue_id, field_id, value)
        await self.session.flush()
