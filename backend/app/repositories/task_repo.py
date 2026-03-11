"""Task repository - data access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.db_models import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository for Task CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)

    async def get_by_id_full(self, task_id: str) -> Task | None:
        """Get task by ID with all relationships eagerly loaded."""
        stmt = (
            select(Task)
            .options(
                joinedload(Task.task_type),
                joinedload(Task.task_status),
                joinedload(Task.assignee_user),
                joinedload(Task.reporter),
                selectinload(Task.children),
            )
            .where(Task.id == task_id)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalars().first()

    async def list_with_filters(
        self,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        assignee_id: str | None = None,
        reporter_id: str | None = None,
        type_id: str | None = None,
        severity: str | None = None,
        session_id: str | None = None,
        project_id: str | None = None,
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
        if assignee_id:
            query = query.where(Task.assignee_id == assignee_id)
        if reporter_id:
            query = query.where(Task.reporter_id == reporter_id)
        if type_id:
            query = query.where(Task.type_id == type_id)
        if severity:
            query = query.where(Task.severity == severity)
        if session_id:
            query = query.where(Task.session_id == session_id)
        if project_id:
            query = query.where(Task.project_id == project_id)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[Task]:
        """Search tasks by title or description (ILIKE)."""
        pattern = f"%{query}%"
        stmt = (
            select(Task)
            .where(
                (Task.title.ilike(pattern)) | (Task.description.ilike(pattern))
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_tasks(self, project_id: str | None = None) -> list[Task]:
        """Get all tasks (for board view)."""
        query = select(Task)
        if project_id:
            query = query.where(Task.project_id == project_id)
        result = await self.session.execute(query)
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

    async def get_children(self, parent_id: str) -> list[Task]:
        """Get direct child tasks."""
        query = select(Task).where(Task.parent_id == parent_id).order_by(Task.created_at)
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
