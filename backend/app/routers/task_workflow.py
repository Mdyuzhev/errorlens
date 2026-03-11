"""Task workflow router — status transitions and workflow validation."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class MoveByStatusId(BaseModel):
    status_id: str


@router.get("/{task_id}/allowed-transitions")
async def get_allowed_transitions(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get statuses the task can transition to."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from app.services.task_workflow_service import TaskWorkflowService
    workflow = TaskWorkflowService(db)
    statuses = await workflow.get_allowed_transitions(task)
    return [
        {"id": s.id, "name": s.name, "slug": s.slug, "color": s.color}
        for s in statuses
    ]


@router.patch("/{task_id}/move")
async def move_task(
    task_id: str,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Move task to new status (Kanban operation)."""
    if not status:
        raise HTTPException(status_code=400, detail="Status is required")
    service = TaskService(db)
    task = await service.move_task(task_id, status, actor_id=user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or invalid status")
    return {"message": f"Task moved to {status}"}


@router.patch("/{task_id}/move-status")
async def move_task_by_status_id(
    task_id: str,
    data: MoveByStatusId,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Move task to new status by status_id with workflow validation."""
    service = TaskService(db)
    task = await service.move_task_by_status_id(task_id, data.status_id, actor_id=user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or invalid status")
    return {"message": "Task status updated"}
