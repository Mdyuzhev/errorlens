"""Sprint business logic — start, complete, burndown, velocity."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Sprint, SprintIssue, Task
from app.repositories.sprint_repo import SprintIssueRepository, SprintRepository


class SprintService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SprintRepository(db)
        self.issue_repo = SprintIssueRepository(db)

    # --- CRUD helpers ---

    async def get_sprint(self, sprint_id: str) -> Sprint | None:
        return await self.repo.get_by_id(sprint_id)

    async def list_sprints(
        self, project_id: str, status: str | None = None
    ) -> list[Sprint]:
        return await self.repo.list_by_project(project_id, status)

    async def create_sprint(self, **data) -> Sprint:
        return await self.repo.create(data)

    async def update_sprint(self, sprint_id: str, **data) -> Sprint | None:
        return await self.repo.update(sprint_id, data)

    async def delete_sprint(self, sprint_id: str) -> bool:
        return await self.repo.delete(sprint_id)

    # --- Sprint lifecycle ---

    async def start_sprint(self, sprint_id: str) -> Sprint:
        """Start a sprint. Only one active sprint per project allowed."""
        sprint = await self.repo.get_by_id(sprint_id)
        if not sprint:
            raise ValueError("Sprint not found")

        if sprint.status != "planned":
            raise ValueError(f"Cannot start sprint in status '{sprint.status}'")

        active = await self.repo.get_active_sprint(sprint.project_id)
        if active:
            raise ValueError(
                f"Project already has active sprint: {active.name}"
            )

        update_data = {"status": "active"}
        if not sprint.start_date:
            update_data["start_date"] = datetime.utcnow()

        return await self.repo.update(sprint_id, update_data)

    async def complete_sprint(
        self, sprint_id: str, next_sprint_id: str | None = None
    ) -> Sprint:
        """Complete sprint, move incomplete tasks to next sprint or backlog."""
        sprint = await self.repo.get_by_id(sprint_id)
        if not sprint:
            raise ValueError("Sprint not found")

        if sprint.status != "active":
            raise ValueError(f"Cannot complete sprint in status '{sprint.status}'")

        # Load sprint issues with their tasks (eager load task_status)
        issues = await self.issue_repo.list_by_sprint(sprint_id)
        task_ids = [si.issue_id for si in issues]

        incomplete_ids: list[str] = []
        if task_ids:
            q = (
                select(Task)
                .where(Task.id.in_(task_ids))
                .options(selectinload(Task.task_status))
            )
            result = await self.db.execute(q)
            tasks = list(result.scalars().all())

            for task in tasks:
                is_done = False
                if task.task_status:
                    is_done = task.task_status.is_final
                else:
                    is_done = task.status == "done"

                if not is_done:
                    incomplete_ids.append(task.id)

        # Move incomplete to next sprint or remove from sprint (backlog)
        if incomplete_ids and next_sprint_id:
            next_sprint = await self.repo.get_by_id(next_sprint_id)
            if not next_sprint:
                raise ValueError("Next sprint not found")

            existing = await self.issue_repo.list_by_sprint(next_sprint_id)
            max_rank = max((si.rank for si in existing), default=0)

            for i, task_id in enumerate(incomplete_ids):
                # Check not already in next sprint
                link = await self.issue_repo.get_by_sprint_and_issue(
                    next_sprint_id, task_id
                )
                if not link:
                    await self.issue_repo.create(
                        {
                            "sprint_id": next_sprint_id,
                            "issue_id": task_id,
                            "rank": max_rank + i + 1,
                        }
                    )

        # Mark sprint completed
        update_data = {"status": "completed"}
        if not sprint.end_date:
            update_data["end_date"] = datetime.utcnow()

        return await self.repo.update(sprint_id, update_data)

    # --- Analytics ---

    async def get_burndown_data(self, sprint_id: str) -> list[dict]:
        """Generate burndown chart data for a sprint."""
        sprint = await self.repo.get_by_id(sprint_id)
        if not sprint or not sprint.start_date:
            return []

        end = sprint.end_date or datetime.utcnow()
        total_days = max((end - sprint.start_date).days, 1)

        # Load sprint issues and tasks
        issues = await self.issue_repo.list_by_sprint(sprint_id)
        task_ids = [si.issue_id for si in issues]

        if not task_ids:
            return []

        q = (
            select(Task)
            .where(Task.id.in_(task_ids))
            .options(selectinload(Task.task_status))
        )
        result = await self.db.execute(q)
        tasks = list(result.scalars().all())

        total_points = len(tasks)
        ideal_per_day = total_points / total_days

        burndown: list[dict] = []
        current = sprint.start_date.replace(hour=0, minute=0, second=0)

        for day_idx in range(total_days + 1):
            day = current + timedelta(days=day_idx)
            ideal = max(total_points - ideal_per_day * day_idx, 0)

            # Count tasks completed by this day
            completed = 0
            for task in tasks:
                if task.completed_at and task.completed_at <= day.replace(
                    hour=23, minute=59, second=59
                ):
                    completed += 1

            burndown.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "ideal_points": round(ideal, 1),
                    "actual_points": total_points - completed,
                }
            )

        return burndown

    async def get_velocity_data(
        self, project_id: str, limit: int = 5
    ) -> list[dict]:
        """Get velocity data for last N completed sprints."""
        q = (
            select(Sprint)
            .where(Sprint.project_id == project_id, Sprint.status == "completed")
            .order_by(Sprint.end_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(q)
        sprints = list(result.scalars().all())

        velocity: list[dict] = []
        for sprint in reversed(sprints):
            issues = await self.issue_repo.list_by_sprint(sprint.id)
            task_ids = [si.issue_id for si in issues]

            completed_count = 0
            if task_ids:
                tq = (
                    select(Task)
                    .where(Task.id.in_(task_ids))
                    .options(selectinload(Task.task_status))
                )
                tres = await self.db.execute(tq)
                for task in tres.scalars().all():
                    is_done = (
                        task.task_status.is_final
                        if task.task_status
                        else task.status == "done"
                    )
                    if is_done:
                        completed_count += 1

            velocity.append(
                {
                    "sprint_id": sprint.id,
                    "sprint_name": sprint.name,
                    "total": len(task_ids),
                    "completed": completed_count,
                    "start_date": (
                        sprint.start_date.isoformat() if sprint.start_date else None
                    ),
                    "end_date": (
                        sprint.end_date.isoformat() if sprint.end_date else None
                    ),
                }
            )

        return velocity
