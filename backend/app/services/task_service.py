"""Task service - business logic layer."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task
from app.repositories.task_repo import TaskRepository
from app.services.project_service import ProjectService

# Valid status transitions for Kanban
VALID_STATUSES = ["todo", "in_progress", "review", "done"]
VALID_PRIORITIES = ["low", "medium", "high"]


class TaskService:
    """Service for task business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskRepository(db)

    async def create_task(
        self,
        title: str,
        description: str | None = None,
        status: str = "todo",
        priority: str = "medium",
        assignee: str | None = None,
        labels: list[str] | None = None,
        due_date: datetime | None = None,
        session_id: str | None = None,
        testcase_id: str | None = None,
        project_id: str | None = None,
    ) -> Task:
        """Create new task."""
        # Validate status and priority
        if status not in VALID_STATUSES:
            status = "todo"
        if priority not in VALID_PRIORITIES:
            priority = "medium"

        task_data = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "labels": labels or [],
            "due_date": due_date,
            "session_id": session_id,
            "testcase_id": testcase_id,
            "project_id": project_id,
        }

        # Generate human_id if project has a key
        if project_id:
            project_service = ProjectService(self.db)
            human_id = await project_service.next_human_id(project_id)
            if human_id:
                task_data["human_id"] = human_id

        task = await self.repo.create(task_data)
        await self.db.commit()
        return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        return await self.repo.get_by_id(task_id)

    async def list_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tasks with filters."""
        tasks = await self.repo.list_with_filters(
            status=status,
            priority=priority,
            assignee=assignee,
            session_id=session_id,
        )
        return [self._to_list_dict(t) for t in tasks]

    async def search_tasks(
        self,
        q: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search tasks by title or description."""
        tasks = await self.repo.search(q, limit=limit)
        return [self._to_list_dict(t) for t in tasks]

    async def get_board(self) -> dict[str, list[dict[str, Any]]]:
        """Get tasks grouped by status for Kanban board."""
        tasks = await self.repo.get_all_tasks()

        board = {status: [] for status in VALID_STATUSES}

        for task in tasks:
            task_dict = self._to_list_dict(task)
            if task.status in board:
                board[task.status].append(task_dict)

        return board

    async def update_task(self, task_id: str, **updates) -> Task | None:
        """Update task fields."""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None

        old_status = task.status

        for key, value in updates.items():
            if value is not None:
                setattr(task, key, value)

        # Set completed_at when moving to done
        new_status = updates.get("status")
        if new_status == "done" and old_status != "done" and not task.completed_at:
            task.completed_at = datetime.utcnow()

        # Clear completed_at if moving out of done
        if new_status and new_status != "done" and task.completed_at:
            task.completed_at = None

        task.updated_at = datetime.utcnow()
        await self.db.commit()
        return task

    async def move_task(self, task_id: str, new_status: str) -> Task | None:
        """Move task to new status (Kanban operation)."""
        if new_status not in VALID_STATUSES:
            return None
        return await self.update_task(task_id, status=new_status)

    async def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        deleted = await self.repo.delete(task_id)
        if deleted:
            await self.db.commit()
        return deleted

    async def get_stats(self) -> dict[str, int]:
        """Get task counts by status."""
        return await self.repo.count_by_status()

    def _to_list_dict(self, task: Task) -> dict[str, Any]:
        """Convert task to list response dict."""
        return {
            "id": task.id,
            "human_id": task.human_id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "assignee": task.assignee,
            "labels": task.labels,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }

    def to_detail_dict(self, task: Task) -> dict[str, Any]:
        """Convert task to detailed response dict."""
        result = self._to_list_dict(task)
        result["session_id"] = task.session_id
        result["testcase_id"] = task.testcase_id
        return result
