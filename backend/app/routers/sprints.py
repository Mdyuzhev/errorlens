"""Sprint API router — thin controller."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import check_project_access, get_default_project, require_auth
from app.models.user import User
from app.services.sprint_service import SprintService

router = APIRouter(prefix="/api/v1/sprints", tags=["sprints"])


# --- Schemas ---


class CreateSprintRequest(BaseModel):
    project_id: str
    name: str
    goal: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class UpdateSprintRequest(BaseModel):
    name: str | None = None
    goal: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class CompleteSprintRequest(BaseModel):
    next_sprint_id: str | None = None


# --- Endpoints ---


@router.get("")
async def list_sprints(
    project_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List sprints for a project."""
    if not project_id:
        project = await get_default_project(user, db)
        if not project:
            return []
        project_id = project.id

    await check_project_access(project_id, user, db)
    service = SprintService(db)
    sprints = await service.list_sprints(project_id, status)
    return [_sprint_to_dict(s) for s in sprints]


@router.post("")
async def create_sprint(
    data: CreateSprintRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a new sprint."""
    await check_project_access(data.project_id, user, db)
    service = SprintService(db)
    sprint = await service.create_sprint(
        project_id=data.project_id,
        name=data.name,
        goal=data.goal,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    return _sprint_to_dict(sprint)


@router.get("/velocity")
async def get_velocity(
    project_id: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get velocity data for last N completed sprints."""
    if not project_id:
        project = await get_default_project(user, db)
        if not project:
            return []
        project_id = project.id

    await check_project_access(project_id, user, db)
    service = SprintService(db)
    return await service.get_velocity_data(project_id, limit)


@router.get("/{sprint_id}")
async def get_sprint(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get sprint detail."""
    service = SprintService(db)
    sprint = await service.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    await check_project_access(sprint.project_id, user, db)
    return _sprint_to_dict(sprint)


@router.put("/{sprint_id}")
async def update_sprint(
    sprint_id: str,
    data: UpdateSprintRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update sprint."""
    service = SprintService(db)
    sprint = await service.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    await check_project_access(sprint.project_id, user, db)

    updated = await service.update_sprint(
        sprint_id, **data.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return _sprint_to_dict(updated)


@router.delete("/{sprint_id}", status_code=204)
async def delete_sprint(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete sprint (only planned sprints)."""
    service = SprintService(db)
    sprint = await service.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    if sprint.status != "planned":
        raise HTTPException(
            status_code=409, detail="Only planned sprints can be deleted"
        )
    await check_project_access(sprint.project_id, user, db)
    await service.delete_sprint(sprint_id)


@router.post("/{sprint_id}/start")
async def start_sprint(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Start a sprint."""
    service = SprintService(db)
    sprint = await service.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    await check_project_access(sprint.project_id, user, db)

    try:
        started = await service.start_sprint(sprint_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _sprint_to_dict(started)


@router.post("/{sprint_id}/complete")
async def complete_sprint(
    sprint_id: str,
    data: CompleteSprintRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Complete a sprint, optionally moving incomplete tasks to next sprint."""
    service = SprintService(db)
    sprint = await service.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    await check_project_access(sprint.project_id, user, db)

    try:
        completed = await service.complete_sprint(sprint_id, data.next_sprint_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _sprint_to_dict(completed)


@router.get("/{sprint_id}/burndown")
async def get_burndown(
    sprint_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get burndown chart data for a sprint."""
    service = SprintService(db)
    sprint = await service.get_sprint(sprint_id)
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    await check_project_access(sprint.project_id, user, db)
    return await service.get_burndown_data(sprint_id)


# --- Helpers ---


def _sprint_to_dict(sprint) -> dict:
    return {
        "id": sprint.id,
        "project_id": sprint.project_id,
        "name": sprint.name,
        "goal": sprint.goal,
        "start_date": sprint.start_date.isoformat() if sprint.start_date else None,
        "end_date": sprint.end_date.isoformat() if sprint.end_date else None,
        "status": sprint.status,
        "created_at": sprint.created_at.isoformat() if sprint.created_at else None,
    }
