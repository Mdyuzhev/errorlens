"""Task settings router — types, statuses, transitions."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.db_models import Task
from app.models.user import User
from app.repositories.task_type_repo import TaskTypeRepository
from app.services.task_workflow_service import TaskWorkflowService

router = APIRouter(prefix="/task-settings", tags=["task-settings"])


# ---- Schemas ----

class TaskTypeCreate(BaseModel):
    name: str
    slug: str
    icon: str = "check-square"
    color: str = "#3b82f6"
    sort_order: int = 0

class TaskTypeUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None

class TaskStatusCreate(BaseModel):
    name: str
    slug: str
    color: str = "#6b7280"
    sort_order: int = 0
    is_initial: bool = False
    is_final: bool = False

class TaskStatusUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    sort_order: int | None = None
    is_initial: bool | None = None
    is_final: bool | None = None

class TransitionCreate(BaseModel):
    from_status_id: str
    to_status_id: str

class TransitionDelete(BaseModel):
    from_status_id: str
    to_status_id: str


# ---- Type endpoints ----

@router.get("/types")
async def list_types(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    types = await repo.get_types(project_id)
    return [_type_to_dict(t) for t in types]


@router.post("/types")
async def create_type(
    data: TaskTypeCreate,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    existing = await repo.get_type_by_slug(project_id, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Type slug already exists")
    task_type = await repo.create_type({**data.model_dump(), "project_id": project_id})
    await db.commit()
    return _type_to_dict(task_type)


@router.put("/types/{type_id}")
async def update_type(
    type_id: str,
    data: TaskTypeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    task_type = await repo.update_type(type_id, data.model_dump(exclude_unset=True))
    if not task_type:
        raise HTTPException(status_code=404, detail="Type not found")
    await db.commit()
    return _type_to_dict(task_type)


# ---- Status endpoints ----

@router.get("/types/{type_id}/statuses")
async def list_statuses(
    type_id: str,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    statuses = await repo.get_statuses(project_id, type_id)
    return [_status_to_dict(s) for s in statuses]


@router.post("/types/{type_id}/statuses")
async def create_status(
    type_id: str,
    data: TaskStatusCreate,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    status = await repo.create_status({
        **data.model_dump(),
        "project_id": project_id,
        "task_type_id": type_id,
    })
    await db.commit()
    return _status_to_dict(status)


@router.put("/statuses/{status_id}")
async def update_status(
    status_id: str,
    data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    status = await repo.update_status(status_id, data.model_dump(exclude_unset=True))
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    await db.commit()
    return _status_to_dict(status)


@router.delete("/statuses/{status_id}")
async def delete_status(
    status_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    from sqlalchemy import func, select
    count_q = select(func.count()).select_from(Task).where(Task.status_id == status_id)
    result = await db.execute(count_q)
    count = result.scalar() or 0
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: {count} tasks use this status")

    repo = TaskTypeRepository(db)
    deleted = await repo.delete_status(status_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Status not found")
    await db.commit()
    return {"message": "Status deleted"}


# ---- Transition endpoints ----

@router.get("/types/{type_id}/transitions")
async def list_transitions(
    type_id: str,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    transitions = await repo.get_transitions(project_id, type_id)
    return [
        {
            "id": t.id,
            "from_status_id": t.from_status_id,
            "to_status_id": t.to_status_id,
        }
        for t in transitions
    ]


@router.post("/types/{type_id}/transitions")
async def create_transition(
    type_id: str,
    data: TransitionCreate,
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    transition = await repo.create_transition(
        data.from_status_id, data.to_status_id, project_id
    )
    await db.commit()
    return {"id": transition.id, "from_status_id": transition.from_status_id, "to_status_id": transition.to_status_id}


@router.delete("/types/{type_id}/transitions")
async def delete_transition(
    type_id: str,
    data: TransitionDelete,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    repo = TaskTypeRepository(db)
    deleted = await repo.delete_transition(data.from_status_id, data.to_status_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transition not found")
    await db.commit()
    return {"message": "Transition deleted"}


# ---- Seed endpoint ----

@router.post("/seed")
async def seed_defaults(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    service = TaskWorkflowService(db)
    await service.seed_defaults(project_id)
    await db.commit()
    return {"message": "Default types and statuses created"}


# ---- Helpers ----

def _type_to_dict(t) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "name": t.name,
        "slug": t.slug,
        "icon": t.icon,
        "color": t.color,
        "sort_order": t.sort_order,
        "is_active": t.is_active,
        "statuses": [_status_to_dict(s) for s in t.statuses] if t.statuses else [],
    }


def _status_to_dict(s) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "slug": s.slug,
        "color": s.color,
        "sort_order": s.sort_order,
        "is_initial": s.is_initial,
        "is_final": s.is_final,
    }
