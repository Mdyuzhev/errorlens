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


@router.get("/velocity")
async def get_velocity(
    project_id: str = Query(...),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Last N completed sprints velocity (committed vs completed story points)."""
    from sqlalchemy.orm import selectinload

    q = (
        select(Sprint)
        .where(Sprint.project_id == project_id, Sprint.status == "completed")
        .order_by(Sprint.end_date.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    sprints = result.scalars().all()

    from app.models.task import Task

    velocity = []
    for s in sprints:
        si_q = select(SprintIssue.issue_id).where(SprintIssue.sprint_id == s.id)
        si_result = await db.execute(si_q)
        issue_ids = [r[0] for r in si_result.all()]
        if not issue_ids:
            velocity.append({
                "sprint_id": s.id, "name": s.name,
                "committed": 0, "completed": 0,
            })
            continue

        tasks_q = select(Task).where(Task.id.in_(issue_ids))
        tasks_result = await db.execute(tasks_q)
        tasks = tasks_result.scalars().all()

        committed = sum(t.story_points or 0 for t in tasks)
        completed = sum(t.story_points or 0 for t in tasks if t.status == "done" or (t.task_status and t.task_status.is_final))
        velocity.append({
            "sprint_id": s.id, "name": s.name,
            "committed": committed, "completed": completed,
        })
    return velocity


@router.get("/{sprint_id}/burndown")
async def get_burndown(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Daily burndown data (ideal vs actual remaining points)."""
    from datetime import date, timedelta
    from app.models.task import Task

    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    if not sprint.start_date or not sprint.end_date:
        return {"error": "Sprint has no start/end dates"}

    start = sprint.start_date.date() if hasattr(sprint.start_date, 'date') else sprint.start_date
    end = sprint.end_date.date() if hasattr(sprint.end_date, 'date') else sprint.end_date

    si_q = select(SprintIssue.issue_id).where(SprintIssue.sprint_id == sprint_id)
    si_result = await db.execute(si_q)
    issue_ids = [r[0] for r in si_result.all()]

    tasks_q = select(Task).where(Task.id.in_(issue_ids)) if issue_ids else select(Task).where(Task.id == None)
    tasks_result = await db.execute(tasks_q)
    tasks = tasks_result.scalars().all()

    total_points = sum(t.story_points or 0 for t in tasks)
    total_days = (end - start).days or 1

    burndown = []
    current = start
    while current <= end:
        day_offset = (current - start).days
        ideal = total_points - (total_points * day_offset / total_days)

        completed_points = sum(
            t.story_points or 0 for t in tasks
            if t.completed_at and t.completed_at.date() <= current
        )
        actual = total_points - completed_points

        burndown.append({
            "date": current.isoformat(),
            "ideal": round(ideal, 1),
            "actual": actual,
        })
        current += timedelta(days=1)
    return {"sprint_id": sprint_id, "total_points": total_points, "burndown": burndown}


@router.get("/{sprint_id}/issues")
async def get_sprint_issues(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Full issue list for sprint Gantt with type, status, assignee."""
    from sqlalchemy.orm import joinedload
    from app.models.task import Task

    sprint = await db.get(Sprint, sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    si_q = select(SprintIssue.issue_id).where(SprintIssue.sprint_id == sprint_id)
    si_result = await db.execute(si_q)
    issue_ids = [r[0] for r in si_result.all()]

    if not issue_ids:
        return []

    tasks_q = (
        select(Task)
        .options(
            joinedload(Task.task_type),
            joinedload(Task.task_status),
            joinedload(Task.assignee_user),
        )
        .where(Task.id.in_(issue_ids))
    )
    tasks_result = await db.execute(tasks_q)
    tasks = tasks_result.unique().scalars().all()

    return [
        {
            "id": t.id,
            "human_id": t.human_id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "story_points": t.story_points,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "type": {"id": t.task_type.id, "name": t.task_type.name, "icon": t.task_type.icon} if t.task_type else None,
            "status_obj": {"id": t.task_status.id, "name": t.task_status.name, "color": t.task_status.color} if t.task_status else None,
            "assignee": {"id": t.assignee_user.id, "display_name": t.assignee_user.display_name} if t.assignee_user else None,
        }
        for t in tasks
    ]


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
