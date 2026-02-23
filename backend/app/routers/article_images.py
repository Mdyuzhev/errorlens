"""Article images router — upload, serve, delete, list."""

import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import (
    check_project_access,
    get_default_project,
    require_auth,
)
from app.models.db_models import ArticleImage
from app.models.user import User
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/articles/images", tags=["article-images"])


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Singleton storage service."""
    return StorageService()


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    article_id: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Upload image to S3 storage."""
    default_project = await get_default_project(user, db)
    if not default_project:
        raise HTTPException(status_code=400, detail="No default project found")

    project_id = default_project.id
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    storage = get_storage_service()
    try:
        result = storage.upload_image(
            file_content=content,
            filename=file.filename or "image.png",
            content_type=content_type,
            project_id=project_id,
        )
    except ValueError as e:
        status = 413 if "too large" in str(e).lower() else 400
        raise HTTPException(status_code=status, detail=str(e))

    # Save metadata to DB
    image = ArticleImage(
        object_key=result.object_key,
        original_filename=result.filename,
        content_type=result.content_type,
        size_bytes=result.size_bytes,
        width=result.width,
        height=result.height,
        project_id=project_id,
        article_id=article_id,
        uploaded_by=user.id,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    return {
        "id": image.id,
        "url": result.url,
        "filename": result.filename,
        "width": result.width,
        "height": result.height,
    }


@router.get("/{project_id}/{filename}")
async def serve_image(project_id: str, filename: str):
    """Serve image from S3 (public, no auth)."""
    object_key = f"{project_id}/{filename}"
    storage = get_storage_service()

    try:
        content, content_type = storage.get_image(object_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")

    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.delete("/{image_id}")
async def delete_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete image from S3 and DB."""
    result = await db.execute(
        select(ArticleImage).where(ArticleImage.id == image_id)
    )
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    await check_project_access(image.project_id, user, db, required_role="member")

    storage = get_storage_service()
    storage.delete_image(image.object_key)

    await db.delete(image)
    await db.commit()

    return Response(status_code=204)


# Separate router for article-scoped image listing (no /images prefix conflict)
list_router = APIRouter(tags=["article-images"])


@list_router.get("/articles/{article_id}/images")
async def list_article_images(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List images attached to an article."""
    result = await db.execute(
        select(ArticleImage).where(ArticleImage.article_id == article_id)
    )
    images = result.scalars().all()

    return [
        {
            "id": img.id,
            "url": f"/api/articles/images/{img.object_key}",
            "filename": img.original_filename,
            "width": img.width,
            "height": img.height,
            "size_bytes": img.size_bytes,
            "created_at": img.created_at.isoformat() if img.created_at else None,
        }
        for img in images
    ]
