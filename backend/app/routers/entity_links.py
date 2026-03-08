"""Entity links router — preview and backlinks endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.entity_link_service import EntityLinkService

router = APIRouter(prefix="/entities", tags=["entities"])

EntityType = Literal["article", "testcase", "task"]


class EntityPreviewResponse(BaseModel):
    id: str
    type: str
    title: str
    status: str | None = None


class BacklinkItem(BaseModel):
    article_id: str
    article_title: str


class BacklinksResponse(BaseModel):
    items: list[BacklinkItem]
    total: int


@router.get("/{entity_type}/{entity_id}/preview", response_model=EntityPreviewResponse)
async def get_entity_preview(
    entity_type: EntityType,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> EntityPreviewResponse:
    """Get preview data for an entity."""
    service = EntityLinkService(db)
    preview = await service.get_entity_preview(entity_type, entity_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityPreviewResponse(**preview)


@router.get("/{entity_type}/{entity_id}/backlinks", response_model=BacklinksResponse)
async def get_entity_backlinks(
    entity_type: EntityType,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> BacklinksResponse:
    """Get articles that reference this entity."""
    service = EntityLinkService(db)
    items = await service.get_backlinks(entity_type, entity_id)
    return BacklinksResponse(
        items=[BacklinkItem(**item) for item in items],
        total=len(items),
    )
