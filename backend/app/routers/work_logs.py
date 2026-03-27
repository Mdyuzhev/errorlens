"""Work logs (time tracking) router."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import WorkLog
from app.models.user import User

router = APIRouter(prefix="/api/v1/work-logs", tags=["work-logs"])


class WorkLogCreate(BaseModel):
    issue_id: str
    hours: float
    log_date: str
    comment: str | None = None


class WorkLogUpdate(BaseModel):
    hours: float | None = None
    log_date: str | None = None
    comment: str | None = None


@router.get("/issues/{issue_id}")
async def list_work_logs(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List work logs for an issue."""
    q = select(WorkLog).where(WorkLog.issue_id == issue_id).order_by(WorkLog.log_date.desc())
    result = await db.execute(q)
    return [
        {
            "id": w.id, "hours": w.hours,
            "log_date": w.log_date.isoformat() if w.log_date else None,
            "comment": w.comment, "user_id": w.user_id,
        }
        for w in result.scalars().all()
    ]


@router.post("")
async def create_work_log(
    data: WorkLogCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Log time on an issue."""
    wl = WorkLog(
        issue_id=data.issue_id, user_id=user.id, hours=data.hours,
        log_date=datetime.fromisoformat(data.log_date), comment=data.comment,
    )
    db.add(wl)
    await db.commit()
    await db.refresh(wl)
    return {"id": wl.id, "message": "Work log created"}


@router.get("/project")
async def get_project_work_logs(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Aggregated work log report grouped by user with task details."""
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    from app.models.task import Task
    from app.models.user import User as UserModel

    q = (
        select(WorkLog)
        .options(joinedload(WorkLog.task))
        .join(Task, WorkLog.issue_id == Task.id)
        .where(Task.project_id == project_id)
        .order_by(WorkLog.log_date.desc())
    )
    result = await db.execute(q)
    logs = result.unique().scalars().all()

    by_user: dict[str, dict] = {}
    for wl in logs:
        uid = wl.user_id or "unknown"
        if uid not in by_user:
            by_user[uid] = {"user_id": uid, "total_hours": 0.0, "entries": []}
        by_user[uid]["total_hours"] += wl.hours
        by_user[uid]["entries"].append({
            "id": wl.id,
            "hours": wl.hours,
            "log_date": wl.log_date.isoformat() if wl.log_date else None,
            "comment": wl.comment,
            "task": {
                "id": wl.task.id,
                "human_id": wl.task.human_id,
                "title": wl.task.title,
            } if wl.task else None,
        })
    return list(by_user.values())


@router.put("/{log_id}")
async def update_work_log(
    log_id: str,
    data: WorkLogUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update a work log entry."""
    wl = await db.get(WorkLog, log_id)
    if not wl:
        raise HTTPException(status_code=404, detail="Work log not found")
    updates = data.model_dump(exclude_unset=True)
    if "log_date" in updates and updates["log_date"]:
        updates["log_date"] = datetime.fromisoformat(updates["log_date"])
    for k, v in updates.items():
        setattr(wl, k, v)
    await db.commit()
    return {"message": "Work log updated"}


@router.delete("/{log_id}")
async def delete_work_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete a work log entry."""
    wl = await db.get(WorkLog, log_id)
    if not wl:
        raise HTTPException(status_code=404, detail="Work log not found")
    await db.delete(wl)
    await db.commit()
    return {"message": "Work log deleted"}
