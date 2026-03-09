"""Repository for task types, statuses, and transitions."""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import TaskType, TaskStatus, StatusTransition


class TaskTypeRepository:
    """Data access for task workflow configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Task Types ----

    async def get_types(self, project_id: str) -> list[TaskType]:
        query = (
            select(TaskType)
            .where(TaskType.project_id == project_id)
            .options(selectinload(TaskType.statuses))
            .order_by(TaskType.sort_order)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_type_by_id(self, type_id: str) -> TaskType | None:
        result = await self.db.execute(
            select(TaskType)
            .where(TaskType.id == type_id)
            .options(selectinload(TaskType.statuses))
        )
        return result.scalar_one_or_none()

    async def get_type_by_slug(self, project_id: str, slug: str) -> TaskType | None:
        result = await self.db.execute(
            select(TaskType).where(
                TaskType.project_id == project_id,
                TaskType.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def create_type(self, data: dict) -> TaskType:
        task_type = TaskType(**data)
        self.db.add(task_type)
        await self.db.flush()
        await self.db.refresh(task_type)
        return task_type

    async def update_type(self, type_id: str, data: dict) -> TaskType | None:
        task_type = await self.get_type_by_id(type_id)
        if not task_type:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(task_type, k, v)
        await self.db.flush()
        return task_type

    # ---- Task Statuses ----

    async def get_statuses(self, project_id: str, task_type_id: str) -> list[TaskStatus]:
        query = (
            select(TaskStatus)
            .where(
                TaskStatus.project_id == project_id,
                TaskStatus.task_type_id == task_type_id,
            )
            .order_by(TaskStatus.sort_order)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_status_by_id(self, status_id: str) -> TaskStatus | None:
        result = await self.db.execute(
            select(TaskStatus).where(TaskStatus.id == status_id)
        )
        return result.scalar_one_or_none()

    async def create_status(self, data: dict) -> TaskStatus:
        status = TaskStatus(**data)
        self.db.add(status)
        await self.db.flush()
        await self.db.refresh(status)
        return status

    async def update_status(self, status_id: str, data: dict) -> TaskStatus | None:
        status = await self.get_status_by_id(status_id)
        if not status:
            return None
        for k, v in data.items():
            if v is not None:
                setattr(status, k, v)
        await self.db.flush()
        return status

    async def delete_status(self, status_id: str) -> bool:
        stmt = delete(TaskStatus).where(TaskStatus.id == status_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    # ---- Transitions ----

    async def get_transitions(self, project_id: str, task_type_id: str) -> list[StatusTransition]:
        status_ids_q = select(TaskStatus.id).where(
            TaskStatus.project_id == project_id,
            TaskStatus.task_type_id == task_type_id,
        )
        query = (
            select(StatusTransition)
            .where(StatusTransition.from_status_id.in_(status_ids_q))
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_transitions_from(self, status_id: str) -> list[StatusTransition]:
        query = select(StatusTransition).where(
            StatusTransition.from_status_id == status_id
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_transition(
        self, from_id: str, to_id: str, project_id: str
    ) -> StatusTransition:
        transition = StatusTransition(
            from_status_id=from_id,
            to_status_id=to_id,
            project_id=project_id,
        )
        self.db.add(transition)
        await self.db.flush()
        await self.db.refresh(transition)
        return transition

    async def delete_transition(self, from_id: str, to_id: str) -> bool:
        stmt = delete(StatusTransition).where(
            StatusTransition.from_status_id == from_id,
            StatusTransition.to_status_id == to_id,
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0
