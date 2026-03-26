"""Components router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import Component
from app.models.user import User

router = APIRouter(prefix="/api/v1/components", tags=["components"])


class ComponentCreate(BaseModel):
    project_id: str
    name: str
    description: str | None = None
    lead_id: str | None = None


class ComponentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    lead_id: str | None = None


@router.get("")
async def list_components(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List components for a project."""
    q = select(Component).where(Component.project_id == project_id).order_by(Component.name)
    result = await db.execute(q)
    return [
        {"id": c.id, "name": c.name, "description": c.description, "lead_id": c.lead_id}
        for c in result.scalars().all()
    ]


@router.post("")
async def create_component(
    data: ComponentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a component."""
    comp = Component(project_id=data.project_id, name=data.name, description=data.description, lead_id=data.lead_id)
    db.add(comp)
    await db.commit()
    await db.refresh(comp)
    return {"id": comp.id, "message": "Component created"}


@router.put("/{component_id}")
async def update_component(
    component_id: str,
    data: ComponentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update component."""
    comp = await db.get(Component, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(comp, k, v)
    await db.commit()
    return {"message": "Component updated"}


@router.delete("/{component_id}")
async def delete_component(
    component_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete component."""
    comp = await db.get(Component, component_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Component not found")
    await db.delete(comp)
    await db.commit()
    return {"message": "Component deleted"}
