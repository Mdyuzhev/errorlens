"""Article folders CRUD router for tree hierarchy.

Folders organize articles in a tree structure (max depth 3).
Multi-tenancy: folders are scoped to projects.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import (
    check_project_access,
    get_default_project,
    require_auth,
)
from app.models.user import User
from app.repositories.article_folder_repo import ArticleFolderRepository
from app.services.article_folder_service import ArticleFolderService
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles/folders", tags=["article-folders"])


class CreateFolderRequest(BaseModel):
    name: str
    parent_id: str | None = None
    project_id: str | None = None


class UpdateFolderRequest(BaseModel):
    name: str


class MoveFolderRequest(BaseModel):
    new_parent_id: str | None = None


class MoveArticleRequest(BaseModel):
    folder_id: str | None = None


@router.get("")
async def get_folders_tree(
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get folder tree for a project."""
    if project_id:
        await check_project_access(project_id, user, db)
        pid = project_id
    else:
        default_project = await get_default_project(user, db)
        if not default_project:
            return {"folders": []}
        pid = default_project.id

    service = ArticleFolderService(db)
    tree = await service.get_tree(pid)
    return {"folders": tree}


@router.post("")
async def create_folder(
    data: CreateFolderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new folder. Requires member role."""
    if data.project_id:
        await check_project_access(data.project_id, user, db, required_role="member")
        pid = data.project_id
    else:
        default_project = await get_default_project(user, db)
        if not default_project:
            raise HTTPException(status_code=400, detail="No project found")
        pid = default_project.id

    service = ArticleFolderService(db)
    folder = await service.create_folder(
        name=data.name,
        project_id=pid,
        parent_id=data.parent_id,
    )
    return {
        "id": folder.id,
        "name": folder.name,
        "parent_id": folder.parent_id,
    }


@router.put("/{folder_id}")
async def update_folder(
    folder_id: str,
    data: UpdateFolderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update folder name. Requires member role."""
    service = ArticleFolderService(db)
    repo = ArticleFolderRepository(db)
    folder = await repo.get_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    await check_project_access(folder.project_id, user, db, required_role="member")

    updated = await service.update_folder(folder_id, data.name, folder.project_id)
    return {
        "id": updated.id,
        "name": updated.name,
        "parent_id": updated.parent_id,
    }


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete folder. Articles move to parent. Requires admin role."""
    repo = ArticleFolderRepository(db)
    folder = await repo.get_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    await check_project_access(folder.project_id, user, db, required_role="admin")

    service = ArticleFolderService(db)
    await service.delete_folder(folder_id)


@router.post("/{folder_id}/move")
async def move_folder(
    folder_id: str,
    data: MoveFolderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Move folder to new parent. Requires member role."""
    repo = ArticleFolderRepository(db)
    folder = await repo.get_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    await check_project_access(folder.project_id, user, db, required_role="member")

    service = ArticleFolderService(db)
    moved = await service.move_folder(folder_id, data.new_parent_id)
    return {
        "id": moved.id,
        "name": moved.name,
        "parent_id": moved.parent_id,
    }


@router.get("/{folder_id}/articles")
async def list_folder_articles(
    folder_id: str,
    exclude: str | None = Query(default=None, description="Article ID to exclude"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List articles in a folder."""
    repo = ArticleFolderRepository(db)
    folder = await repo.get_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    await check_project_access(folder.project_id, user, db)

    service = ArticleService(db)
    return await service.get_folder_articles(
        folder_id, exclude_article_id=exclude, limit=10
    )


# This endpoint is on /articles/{id}/move-to-folder but registered in this router
# with prefix /articles/folders — so we need a separate router for article move
move_router = APIRouter(prefix="/articles", tags=["article-folders"])


@move_router.post("/{article_id}/move-to-folder")
async def move_article_to_folder(
    article_id: str,
    data: MoveArticleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Move article to a folder (or root). Requires member role."""
    from app.repositories.article_repo import ArticleRepository

    article_repo = ArticleRepository(db)
    article = await article_repo.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.project_id:
        await check_project_access(article.project_id, user, db, required_role="member")

    service = ArticleFolderService(db)
    await service.move_article_to_folder(article_id, data.folder_id)
    return {"message": "ok"}
