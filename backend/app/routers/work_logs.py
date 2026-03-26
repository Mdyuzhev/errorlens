"""Work logs API router."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import WorkLog
from app.models.user import User
from app.repositories.task_repo import TaskRepository
from app.repositories.work_log_repo import WorkLogRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/issues", tags=["work-logs"])


class CreateWorkLogRequest(BaseModel):
    hours: float = Field(..., gt=0, description="Hours spent")
    log_date: datetime
    comment: str | None = None


class WorkLogResponse(BaseModel):
    id: str
    issue_id: str
    user_id: str | None
    hours: float
    log_date: str
    comment: str | None
    created_at: str | None


@router.post("/{issue_id}/work-log")
async def create_work_log(
    issue_id: str,
    body: CreateWorkLogRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a work log entry and update task spent_hours."""
    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(issue_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    repo = WorkLogRepository(db)
    log = await repo.create({
        "issue_id": issue_id,
        "user_id": user.id,
        "hours": body.hours,
        "log_date": body.log_date,
        "comment": body.comment,
    })

    new_spent = (task.spent_hours or 0.0) + body.hours
    await task_repo.update(issue_id, {"spent_hours": new_spent})
    await db.commit()

    return _serialize(log)


@router.get("/{issue_id}/work-logs")
async def list_work_logs(
    issue_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List work logs for a task."""
    repo = WorkLogRepository(db)
    items = await repo.list_by_issue(issue_id)
    return [_serialize(w) for w in items]


@router.delete("/{issue_id}/work-logs/{log_id}")
async def delete_work_log(
    issue_id: str,
    log_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete work log and subtract hours from task spent_hours."""
    repo = WorkLogRepository(db)
    log = await repo.get_by_id(log_id)
    if not log or log.issue_id != issue_id:
        raise HTTPException(status_code=404, detail="Work log not found")

    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(issue_id)
    if task:
        new_spent = max(0.0, (task.spent_hours or 0.0) - log.hours)
        await task_repo.update(issue_id, {"spent_hours": new_spent})

    await repo.delete(log_id)
    await db.commit()

    return {"ok": True}


def _serialize(w: WorkLog) -> dict:
    return {
        "id": w.id,
        "issue_id": w.issue_id,
        "user_id": w.user_id,
        "hours": w.hours,
        "log_date": w.log_date.isoformat() if w.log_date else None,
        "comment": w.comment,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }
