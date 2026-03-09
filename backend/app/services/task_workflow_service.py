"""Task workflow service — types, statuses, transitions, seed."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task, TaskStatus
from app.repositories.task_type_repo import TaskTypeRepository

# Default task types with icon and color
DEFAULT_TYPES = [
    {"slug": "task", "name": "Task", "icon": "check-square", "color": "#3b82f6", "sort_order": 0},
    {"slug": "bug", "name": "Bug", "icon": "alert", "color": "#ef4444", "sort_order": 1},
    {"slug": "story", "name": "Story", "icon": "file", "color": "#10b981", "sort_order": 2},
    {"slug": "epic", "name": "Epic", "icon": "clipboard-list", "color": "#8b5cf6", "sort_order": 3},
    {"slug": "release", "name": "Release", "icon": "tag", "color": "#f59e0b", "sort_order": 4},
]

# Default statuses for each type
DEFAULT_STATUSES = [
    {"slug": "todo", "name": "To Do", "color": "#6b7280", "sort_order": 0, "is_initial": True, "is_final": False},
    {"slug": "in_progress", "name": "In Progress", "color": "#3b82f6", "sort_order": 1, "is_initial": False, "is_final": False},
    {"slug": "review", "name": "Review", "color": "#f59e0b", "sort_order": 2, "is_initial": False, "is_final": False},
    {"slug": "done", "name": "Done", "color": "#10b981", "sort_order": 3, "is_initial": False, "is_final": True},
]

# Default transitions: (from_slug, to_slug)
DEFAULT_TRANSITIONS = [
    ("todo", "in_progress"),
    ("in_progress", "review"),
    ("in_progress", "todo"),
    ("review", "done"),
    ("review", "in_progress"),
    ("done", "in_progress"),
]


class TaskWorkflowService:
    """Business logic for task workflow configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskTypeRepository(db)

    async def validate_transition(self, task: Task, new_status_id: str) -> bool:
        """Check if transition from current status to new status is allowed."""
        if not task.status_id:
            return True
        transitions = await self.repo.get_transitions_from(task.status_id)
        return any(t.to_status_id == new_status_id for t in transitions)

    async def get_allowed_transitions(self, task: Task) -> list[TaskStatus]:
        """Get statuses the task can transition to from current status."""
        if not task.status_id:
            return []
        transitions = await self.repo.get_transitions_from(task.status_id)
        statuses = []
        for t in transitions:
            s = await self.repo.get_status_by_id(t.to_status_id)
            if s:
                statuses.append(s)
        return statuses

    async def seed_defaults(self, project_id: str) -> None:
        """Create default task types, statuses, and transitions for a project."""
        for type_data in DEFAULT_TYPES:
            existing = await self.repo.get_type_by_slug(project_id, type_data["slug"])
            if existing:
                continue

            task_type = await self.repo.create_type({
                **type_data,
                "project_id": project_id,
            })

            # Create statuses for this type
            status_map: dict[str, str] = {}
            for st_data in DEFAULT_STATUSES:
                status = await self.repo.create_status({
                    **st_data,
                    "project_id": project_id,
                    "task_type_id": task_type.id,
                })
                status_map[st_data["slug"]] = status.id

            # Create transitions
            for from_slug, to_slug in DEFAULT_TRANSITIONS:
                from_id = status_map.get(from_slug)
                to_id = status_map.get(to_slug)
                if from_id and to_id:
                    await self.repo.create_transition(from_id, to_id, project_id)

    async def get_initial_status(self, task_type_id: str, project_id: str) -> TaskStatus | None:
        """Get the initial status for a task type."""
        statuses = await self.repo.get_statuses(project_id, task_type_id)
        for s in statuses:
            if s.is_initial:
                return s
        return statuses[0] if statuses else None
