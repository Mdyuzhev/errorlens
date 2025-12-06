"""Task repository - data access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository for Task CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)

    async def list_with_filters(
        self,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        session_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with filters."""
        query = select(Task).order_by(Task.created_at.desc())

        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if assignee:
            query = query.where(Task.assignee == assignee)
        if session_id:
            query = query.where(Task.session_id == session_id)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_tasks(self) -> list[Task]:
        """Get all tasks (for board view)."""
        result = await self.session.execute(select(Task))
        return list(result.scalars().all())

    async def get_by_session(self, session_id: str) -> list[Task]:
        """Get tasks linked to a session."""
        query = select(Task).where(Task.session_id == session_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_testcase(self, testcase_id: str) -> list[Task]:
        """Get tasks linked to a test case."""
        query = select(Task).where(Task.testcase_id == testcase_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_status(self) -> dict[str, int]:
        """Count tasks grouped by status."""
        tasks = await self.get_all_tasks()
        counts = {"todo": 0, "in_progress": 0, "review": 0, "done": 0}
        for task in tasks:
            if task.status in counts:
                counts[task.status] += 1
        return counts
