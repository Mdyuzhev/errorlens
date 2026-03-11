"""Saved JQL filters CRUD router."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.db_models import SavedFilter
from app.models.user import User

router = APIRouter(prefix="/saved-filters", tags=["saved-filters"])


class FilterCreate(BaseModel):
    name: str
    jql: str
    project_id: str
    is_shared: bool = False


class FilterUpdate(BaseModel):
    name: str | None = None
    jql: str | None = None
    is_shared: bool | None = None


@router.get("")
async def list_filters(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List user's filters + shared filters for the project."""
    from sqlalchemy import or_

    stmt = select(SavedFilter)
    conditions = [SavedFilter.owner_id == user.id]

    if project_id:
        stmt = stmt.where(SavedFilter.project_id == project_id)
        conditions.append(SavedFilter.is_shared.is_(True))

    stmt = stmt.where(or_(*conditions)).order_by(SavedFilter.created_at.desc())
    result = await db.execute(stmt)
    filters = result.scalars().all()

    return [
        {
            "id": f.id,
            "name": f.name,
            "jql": f.jql,
            "is_shared": f.is_shared,
            "is_own": f.owner_id == user.id,
            "project_id": f.project_id,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in filters
    ]


@router.post("")
async def create_filter(
    data: FilterCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a saved filter."""
    f = SavedFilter(
        owner_id=user.id,
        project_id=data.project_id,
        name=data.name,
        jql=data.jql,
        is_shared=data.is_shared,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return {"id": f.id, "message": "Filter saved"}


@router.put("/{filter_id}")
async def update_filter(
    filter_id: str,
    data: FilterUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update a saved filter (owner only)."""
    result = await db.execute(
        select(SavedFilter).where(SavedFilter.id == filter_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    if f.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")

    if data.name is not None:
        f.name = data.name
    if data.jql is not None:
        f.jql = data.jql
    if data.is_shared is not None:
        f.is_shared = data.is_shared
    f.updated_at = datetime.utcnow()

    await db.commit()
    return {"message": "Filter updated"}


@router.delete("/{filter_id}")
async def delete_filter(
    filter_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete a saved filter (owner or admin)."""
    from sqlalchemy import delete

    result = await db.execute(
        select(SavedFilter).where(SavedFilter.id == filter_id)
    )
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    if f.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed")

    await db.execute(delete(SavedFilter).where(SavedFilter.id == filter_id))
    await db.commit()
    return {"message": "Filter deleted"}
