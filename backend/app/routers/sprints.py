"""Sprint management router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import Sprint, SprintIssue
from app.models.user import User

router = APIRouter(prefix="/api/v1/sprints", tags=["sprints"])


class SprintCreate(BaseModel):
    project_id: str
    name: str
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class SprintUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None


@router.get("")
async def list_sprints(
    project_id: str = Query(...),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List sprints for a project."""
    q = select(Sprint).where(Sprint.project_id == project_id)
    if status:
        q = q.where(Sprint.status == status)
    q = q.order_by(Sprint.created_at.desc())
    result = await db.execute(q)
    sprints = result.scalars().all()
    return [
        {
            "id": s.id, "name": s.name, "goal": s.goal,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "status": s.status, "project_id": s.project_id,
        }
        for s in sprints
    ]


@router.post("")
async def create_sprint(
    data: SprintCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a new sprint."""
    from datetime import datetime

    sprint = Sprint(
        project_id=data.project_id,
        name=data.name,
        goal=data.goal,
        start_date=datetime.fromisoformat(data.start_date) if data.start_date else None,
        end_date=datetime.fromisoformat(data.end_date) if data.end_date else None,
    )
    db.add(sprint)
    await db.commit()
    await db.refresh(sprint)
    return {"id": sprint.id, "message": "Sprint created"}


@router.get("/{sprint_id}")
async def get_sprint(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get sprint with its issues."""
    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    # Get issues in this sprint
    q = select(SprintIssue).where(SprintIssue.sprint_id == sprint_id).order_by(SprintIssue.rank)
    result = await db.execute(q)
    issues = result.scalars().all()
    return {
        "id": sprint.id, "name": sprint.name, "goal": sprint.goal,
        "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
        "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
        "status": sprint.status,
        "issues": [{"issue_id": si.issue_id, "rank": si.rank} for si in issues],
    }


@router.put("/{sprint_id}")
async def update_sprint(
    sprint_id: str,
    data: SprintUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update sprint."""
    from datetime import datetime

    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    updates = data.model_dump(exclude_unset=True)
    for key, val in updates.items():
        if key in ("start_date", "end_date") and val:
            val = datetime.fromisoformat(val)
        setattr(sprint, key, val)
    await db.commit()
    return {"message": "Sprint updated"}


@router.delete("/{sprint_id}")
async def delete_sprint(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete sprint."""
    from sqlalchemy import delete

    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    await db.execute(delete(SprintIssue).where(SprintIssue.sprint_id == sprint_id))
    await db.delete(sprint)
    await db.commit()
    return {"message": "Sprint deleted"}
