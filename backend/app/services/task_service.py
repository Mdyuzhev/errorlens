"""Task service - business logic layer."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task, TaskActivity
from app.repositories.task_repo import TaskRepository
from app.services import event_publisher
from app.services.exceptions import TaskDepthExceededError, TransitionNotAllowedError
from app.services.project_service import ProjectService
from app.services.task_workflow_service import TaskWorkflowService

# Valid status transitions for Kanban (legacy, kept for backward compat)
VALID_STATUSES = ["todo", "in_progress", "review", "done"]
VALID_PRIORITIES = ["low", "medium", "high"]
VALID_SEVERITIES = ["critical", "major", "minor", "trivial"]
VALID_ENVIRONMENTS = ["production", "staging", "local", "all"]

# Fields tracked in activity log
TRACKED_FIELDS = [
    "title", "description", "status", "priority", "assignee", "assignee_id",
    "type_id", "status_id", "severity", "environment", "due_date",
    "estimated_hours", "spent_hours", "parent_id", "labels",
]

MAX_TASK_DEPTH = 4


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
        assignee_id: str | None = None,
        reporter_id: str | None = None,
        labels: list[str] | None = None,
        due_date: datetime | None = None,
        session_id: str | None = None,
        testcase_id: str | None = None,
        project_id: str | None = None,
        type_id: str | None = None,
        severity: str | None = None,
        environment: str | None = None,
        estimated_hours: float | None = None,
        spent_hours: float | None = None,
        parent_id: str | None = None,
    ) -> Task:
        """Create new task."""
        # Validate status and priority
        if status not in VALID_STATUSES:
            status = "todo"
        if priority not in VALID_PRIORITIES:
            priority = "medium"

        # Validate depth if parent_id is set
        if parent_id:
            depth = await self.get_depth(parent_id)
            if depth >= MAX_TASK_DEPTH:
                raise TaskDepthExceededError(
                    f"Maximum task depth ({MAX_TASK_DEPTH}) exceeded"
                )

        task_data: dict[str, Any] = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "assignee_id": assignee_id,
            "reporter_id": reporter_id,
            "labels": labels or [],
            "due_date": due_date,
            "session_id": session_id,
            "testcase_id": testcase_id,
            "project_id": project_id,
            "type_id": type_id,
            "severity": severity,
            "environment": environment,
            "estimated_hours": estimated_hours,
            "spent_hours": spent_hours,
            "parent_id": parent_id,
        }

        # Generate human_id if project has a key
        if project_id:
            project_service = ProjectService(self.db)
            human_id = await project_service.next_human_id(project_id)
            if human_id:
                task_data["human_id"] = human_id

        # Set initial status_id from workflow if type_id is provided
        if type_id and project_id:
            workflow = TaskWorkflowService(self.db)
            initial_status = await workflow.get_initial_status(type_id, project_id)
            if initial_status:
                task_data["status_id"] = initial_status.id
                task_data["status"] = initial_status.slug

        task = await self.repo.create(task_data)
        await self.db.commit()

        # Record creation activity
        await self._record_activity(
            task.id, reporter_id, "created", new_value={"title": title}
        )
        await self.db.commit()

        await event_publisher.publish(
            "task.created",
            {"id": task.id, "title": title, "priority": priority, "assignee_id": assignee_id or assignee},
            project_id=project_id,
        )

        return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID with all relationships."""
        return await self.repo.get_by_id_full(task_id)

    async def list_tasks(
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
    ) -> list[dict[str, Any]]:
        """List tasks with filters."""
        tasks = await self.repo.list_with_filters(
            status=status,
            priority=priority,
            assignee=assignee,
            assignee_id=assignee_id,
            reporter_id=reporter_id,
            type_id=type_id,
            severity=severity,
            session_id=session_id,
            project_id=project_id,
        )
        return [self._to_list_dict(t) for t in tasks]

    async def list_tasks_jql(
        self,
        where_clause: Any,
        order_clauses: list[Any] | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tasks using a compiled JQL WHERE clause."""
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        stmt = select(Task).options(
            joinedload(Task.task_type),
            joinedload(Task.task_status),
            joinedload(Task.assignee_user),
            joinedload(Task.reporter),
        )

        if project_id:
            stmt = stmt.where(Task.project_id == project_id)

        if where_clause is not None:
            stmt = stmt.where(where_clause)

        if order_clauses:
            for clause in order_clauses:
                stmt = stmt.order_by(clause)
        else:
            stmt = stmt.order_by(Task.created_at.desc())

        stmt = stmt.limit(200)
        result = await self.db.execute(stmt)
        tasks = result.unique().scalars().all()
        return [self._to_list_dict(t) for t in tasks]

    async def search_tasks(
        self,
        q: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search tasks by title or description."""
        tasks = await self.repo.search(q, limit=limit)
        return [self._to_list_dict(t) for t in tasks]

    async def get_board(self, project_id: str | None = None, type_slug: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """Get tasks grouped by status for Kanban board."""
        tasks = await self.repo.get_all_tasks(project_id=project_id)

        if type_slug:
            tasks = [t for t in tasks if t.task_type and t.task_type.slug == type_slug]

        board: dict[str, list[dict[str, Any]]] = {status: [] for status in VALID_STATUSES}

        for task in tasks:
            task_dict = self._to_list_dict(task)
            if task.status in board:
                board[task.status].append(task_dict)

        return board

    async def update_task(self, task_id: str, actor_id: str | None = None, **updates) -> Task | None:
        """Update task fields."""
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None

        old_status = task.status
        old_assignee = task.assignee

        # Track changes for activity log
        for field in TRACKED_FIELDS:
            if field in updates:
                old_val = getattr(task, field, None)
                new_val = updates[field]
                if old_val != new_val:
                    await self._record_activity(
                        task_id, actor_id, "field_updated",
                        field_name=field,
                        old_value={"value": str(old_val) if old_val is not None else None},
                        new_value={"value": str(new_val) if new_val is not None else None},
                    )

        for key, value in updates.items():
            if not key.startswith("_"):
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

        # Publish events
        if new_status and new_status != old_status:
            await event_publisher.publish(
                "task.status_changed",
                {
                    "id": task.id, "title": task.title,
                    "old_status": old_status, "new_status": new_status,
                    "from_status_id": updates.get("_old_status_id", ""),
                    "to_status_id": task.status_id or "",
                    "type_id": task.type_id or "",
                    "assignee_id": task.assignee_id or task.assignee,
                },
                project_id=task.project_id,
            )

        new_assignee = updates.get("assignee_id") or updates.get("assignee")
        if new_assignee and new_assignee != old_assignee:
            await event_publisher.publish(
                "task.assigned",
                {
                    "id": task.id, "title": task.title,
                    "old_assignee_id": old_assignee, "new_assignee_id": new_assignee,
                },
                project_id=task.project_id,
            )

        return task

    async def move_task(self, task_id: str, new_status: str, actor_id: str | None = None) -> Task | None:
        """Move task to new status (Kanban operation)."""
        if new_status not in VALID_STATUSES:
            return None

        task = await self.repo.get_by_id(task_id)
        if not task:
            return None

        old_status = task.status

        # Validate workflow transition if status_id is set
        if task.status_id:
            workflow = TaskWorkflowService(self.db)
            allowed = await workflow.get_allowed_transitions(task)
            target = next((s for s in allowed if s.slug == new_status), None)
            if not target:
                raise TransitionNotAllowedError(
                    f"Transition from '{old_status}' to '{new_status}' is not allowed"
                )
            # Update both status_id and status slug
            return await self.update_task(
                task_id, actor_id=actor_id, status=new_status,
                status_id=target.id, _old_status_id=task.status_id or "",
            )

        return await self.update_task(task_id, actor_id=actor_id, status=new_status)

    async def move_task_by_status_id(self, task_id: str, new_status_id: str, actor_id: str | None = None) -> Task | None:
        """Move task to new status by status_id with workflow validation."""
        task = await self.repo.get_by_id_full(task_id)
        if not task:
            return None

        workflow = TaskWorkflowService(self.db)
        if task.status_id:
            result = await workflow.validate_transition(task, new_status_id)
            if not result["allowed"]:
                if result["reason"] == "missing_fields":
                    raise TransitionNotAllowedError(
                        f"Fill required fields before transition: {', '.join(result['fields'])}",
                        fields=result["fields"],
                    )
                raise TransitionNotAllowedError("Status transition not allowed")

        # Get status slug for backward compat
        from app.repositories.task_type_repo import TaskTypeRepository
        repo = TaskTypeRepository(self.db)
        new_status = await repo.get_status_by_id(new_status_id)
        if not new_status:
            return None

        # Record status change activity
        old_status_name = task.status
        if task.task_status:
            old_status_name = task.task_status.name

        await self._record_activity(
            task_id, actor_id, "status_changed",
            old_value={"status": old_status_name},
            new_value={"status": new_status.name},
        )

        return await self.update_task(
            task_id, actor_id=actor_id,
            status=new_status.slug, status_id=new_status_id,
            _old_status_id=task.status_id or "",
        )

    async def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        deleted = await self.repo.delete(task_id)
        if deleted:
            await self.db.commit()
        return deleted

    async def get_stats(self) -> dict[str, int]:
        """Get task counts by status."""
        return await self.repo.count_by_status()

    async def get_children(self, task_id: str) -> list[dict[str, Any]]:
        """Get direct child tasks."""
        tasks = await self.repo.get_children(task_id)
        return [self._to_list_dict(t) for t in tasks]

    async def get_depth(self, task_id: str) -> int:
        """Get task depth using recursive CTE."""
        cte_query = text("""
            WITH RECURSIVE task_tree AS (
                SELECT id, parent_id, 1 AS depth
                FROM tasks
                WHERE id = :task_id
                UNION ALL
                SELECT t.id, t.parent_id, tt.depth + 1
                FROM tasks t
                JOIN task_tree tt ON t.id = tt.parent_id
            )
            SELECT MAX(depth) FROM task_tree
        """)
        result = await self.db.execute(cte_query, {"task_id": task_id})
        depth = result.scalar()
        return depth or 1

    async def _record_activity(
        self,
        task_id: str,
        actor_id: str | None,
        action_type: str,
        field_name: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
    ) -> TaskActivity:
        """Create a TaskActivity record."""
        activity = TaskActivity(
            task_id=task_id,
            actor_id=actor_id,
            action_type=action_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(activity)
        await self.db.flush()
        return activity

    def _to_list_dict(self, task: Task) -> dict[str, Any]:
        """Convert task to list response dict."""
        result: dict[str, Any] = {
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
            # New fields
            "type_id": task.type_id,
            "status_id": task.status_id,
            "assignee_id": task.assignee_id,
            "reporter_id": task.reporter_id,
            "severity": task.severity,
            "environment": task.environment,
            "estimated_hours": task.estimated_hours,
            "spent_hours": task.spent_hours,
            "parent_id": task.parent_id,
        }

        # Include type info if loaded
        if task.task_type:
            result["type"] = {
                "id": task.task_type.id,
                "name": task.task_type.name,
                "slug": task.task_type.slug,
                "icon": task.task_type.icon,
                "color": task.task_type.color,
            }

        # Include status info if loaded
        if task.task_status:
            result["task_status"] = {
                "id": task.task_status.id,
                "name": task.task_status.name,
                "slug": task.task_status.slug,
                "color": task.task_status.color,
            }

        # Include user info if loaded
        if task.assignee_user:
            result["assignee_user"] = {
                "id": task.assignee_user.id,
                "username": task.assignee_user.username,
                "display_name": task.assignee_user.display_name,
            }
        if task.reporter:
            result["reporter"] = {
                "id": task.reporter.id,
                "username": task.reporter.username,
                "display_name": task.reporter.display_name,
            }

        return result

    def to_detail_dict(self, task: Task) -> dict[str, Any]:
        """Convert task to detailed response dict."""
        result = self._to_list_dict(task)
        result["session_id"] = task.session_id
        result["testcase_id"] = task.testcase_id
        result["updated_at"] = task.updated_at.isoformat() if task.updated_at else None

        # Children
        if task.children:
            result["children"] = [
                {"id": c.id, "human_id": c.human_id, "title": c.title, "status": c.status}
                for c in task.children
            ]

        return result
