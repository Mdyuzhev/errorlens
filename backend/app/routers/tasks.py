"""Tasks CRUD router with Kanban board support - thin controller."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    assignee: str | None = None
    labels: list[str] = []
    due_date: datetime | None = None
    session_id: str | None = None
    testcase_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    labels: list[str] | None = None
    due_date: datetime | None = None


@router.get("")
async def list_tasks(
    q: str | None = Query(default=None, description="Search query"),
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List tasks with filters."""
    service = TaskService(db)
    if q:
        return await service.search_tasks(q, limit=20)
    return await service.list_tasks(
        status=status,
        priority=priority,
        assignee=assignee,
    )


@router.get("/board")
async def get_board(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get tasks grouped by status for Kanban board."""
    service = TaskService(db)
    return await service.get_board()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get task counts by status."""
    service = TaskService(db)
    return await service.get_stats()


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get task by ID."""
    service = TaskService(db)
    task = await service.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return service.to_detail_dict(task)


@router.post("")
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new task."""
    service = TaskService(db)
    task = await service.create_task(
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        assignee=data.assignee,
        labels=data.labels,
        due_date=data.due_date,
        session_id=data.session_id,
        testcase_id=data.testcase_id,
    )
    return {"id": task.id, "message": "Task created"}


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update task."""
    service = TaskService(db)
    task = await service.update_task(task_id, **data.model_dump(exclude_unset=True))

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task updated"}


@router.patch("/{task_id}/move")
async def move_task(
    task_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Move task to new status (Kanban operation)."""
    service = TaskService(db)
    task = await service.move_task(task_id, status)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found or invalid status")

    return {"message": f"Task moved to {status}"}


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete task."""
    service = TaskService(db)
    deleted = await service.delete_task(task_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted"}
