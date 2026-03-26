"""Components API router — CRUD for project components."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import check_project_access, require_auth
from app.models.user import User
from app.repositories.component_repo import ComponentRepository

router = APIRouter(prefix="/v1/components", tags=["components"])


# ── Schemas ──────────────────────────────────────────────


class CreateComponentRequest(BaseModel):
    name: str
    description: str | None = None
    lead_id: str | None = None
    project_id: str


class UpdateComponentRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    lead_id: str | None = None


# ── Helpers ──────────────────────────────────────────────


def _component_to_dict(comp) -> dict:
    return {
        "id": comp.id,
        "project_id": comp.project_id,
        "name": comp.name,
        "description": comp.description,
        "lead_id": comp.lead_id,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
    }


# ── Endpoints ────────────────────────────────────────────


@router.get("/")
async def list_components(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all components for a project."""
    await check_project_access(project_id, user, db)
    repo = ComponentRepository(db)
    components = await repo.list_by_project(project_id)
    return [_component_to_dict(c) for c in components]


@router.post("/", status_code=201)
async def create_component(
    body: CreateComponentRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new component."""
    await check_project_access(body.project_id, user, db, required_role="member")
    repo = ComponentRepository(db)

    # Uniqueness check
    existing = await repo.get_by_name(body.name, body.project_id)
    if existing:
        raise HTTPException(status_code=409, detail="Component with this name already exists")

    comp = await repo.create(body.model_dump())
    await db.commit()
    return _component_to_dict(comp)


@router.put("/{component_id}")
async def update_component(
    component_id: str,
    body: UpdateComponentRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a component."""
    repo = ComponentRepository(db)
    comp = await repo.get_by_id(component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")

    await check_project_access(comp.project_id, user, db, required_role="member")

    # Uniqueness check if name changed
    if body.name and body.name != comp.name:
        existing = await repo.get_by_name(body.name, comp.project_id)
        if existing:
            raise HTTPException(status_code=409, detail="Component with this name already exists")

    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = await repo.update(component_id, data)
    await db.commit()
    return _component_to_dict(updated)


@router.delete("/{component_id}", status_code=204)
async def delete_component(
    component_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a component (admin only)."""
    repo = ComponentRepository(db)
    comp = await repo.get_by_id(component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")

    await check_project_access(comp.project_id, user, db, required_role="admin")

    await repo.delete(component_id)
    await db.commit()
