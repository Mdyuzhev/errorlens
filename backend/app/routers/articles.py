"""Articles/Knowledge base CRUD router - thin controller.

Multi-tenancy: Articles are filtered by project_id.
Users can only access articles in projects they own or are members of.
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import (
    check_project_access,
    get_default_project,
    require_auth,
)
from app.models.user import User
from app.services.article_import_service import ArticleImportService
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleCreate(BaseModel):
    title: str
    content: str
    excerpt: str | None = None
    category: str | None = None
    tags: list[str] = []
    status: str = "draft"
    project_id: str | None = None  # Required for multi-tenancy
    folder_id: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None


@router.get("")
async def list_articles(
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    folder_id: str | None = Query(default=None, description="Filter by folder ID"),
    category: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    List articles with filters.

    If project_id provided, filters by that project (requires access).
    If project_id is None, returns articles from user's default project.
    """
    # Determine which project to use
    if project_id:
        await check_project_access(project_id, user, db)
        filter_project_id = project_id
    else:
        default_project = await get_default_project(user, db)
        filter_project_id = default_project.id if default_project else None

    service = ArticleService(db)
    return await service.list_articles(
        project_id=filter_project_id,
        category=category,
        status=status,
        tag=tag,
        folder_id=folder_id,
    )


@router.get("/categories/list")
async def list_categories(
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get unique categories for a project."""
    if project_id:
        await check_project_access(project_id, user, db)
        filter_project_id = project_id
    else:
        default_project = await get_default_project(user, db)
        filter_project_id = default_project.id if default_project else None

    service = ArticleService(db)
    return await service.get_categories(project_id=filter_project_id)


@router.post("/import")
async def import_article(
    file: UploadFile = File(...),
    folder_id: str | None = Form(default=None),
    category: str | None = Form(default=None),
    status: str = Form(default="draft"),
    tags: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Import article from .md or .docx file (quick import as draft)."""
    # Determine project
    default_project = await get_default_project(user, db)
    if not default_project:
        raise HTTPException(
            status_code=400, detail="No default project found"
        )
    project_id = default_project.id

    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    service = ArticleImportService(db)
    article, warnings = await service.import_from_file(
        file=file,
        folder_id=folder_id,
        project_id=project_id,
        author=user.username,
        created_by=user.id,
        category=category,
        status=status,
        tags=tags_list,
    )

    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "content_length": len(article.content or ""),
        "warnings": warnings,
    }


@router.post("/import/preview")
async def import_article_preview(
    file: UploadFile = File(...),
    _user: User = Depends(require_auth),
):
    """Parse file and return title + content without creating article."""
    service = ArticleImportService(None)  # type: ignore[arg-type]
    title, content, warnings = await service.preview_file(file)

    return {
        "title": title,
        "content": content,
        "warnings": warnings,
    }


@router.get("/{article_id}")
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Get article by ID.

    Returns 404 if not found or user has no access to article's project.
    """
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check project access
    if article.project_id:
        await check_project_access(article.project_id, user, db)

    return service.to_detail_dict(article)


@router.post("")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Create new article.

    Requires member role or higher in the project.
    """
    # Determine project
    if data.project_id:
        await check_project_access(data.project_id, user, db, required_role="member")
        project_id = data.project_id
    else:
        default_project = await get_default_project(user, db)
        if not default_project:
            raise HTTPException(
                status_code=400, detail="No project specified and no default project found"
            )
        project_id = default_project.id

    service = ArticleService(db)
    article = await service.create_article(
        title=data.title,
        content=data.content,
        author=user.username,
        excerpt=data.excerpt,
        category=data.category,
        tags=data.tags,
        status=data.status,
        project_id=project_id,
        created_by=user.id,
        folder_id=data.folder_id,
    )
    return {"id": article.id, "slug": article.slug}


@router.put("/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Update article.

    Requires member role or higher in the article's project.
    """
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check project access with member role
    if article.project_id:
        await check_project_access(article.project_id, user, db, required_role="member")

    updated = await service.update_article(article_id, **data.model_dump(exclude_unset=True))

    if not updated:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article updated"}


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Delete article.

    Requires admin role or higher in the article's project.
    """
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check project access with admin role for delete
    if article.project_id:
        await check_project_access(article.project_id, user, db, required_role="admin")

    deleted = await service.delete_article(article_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article deleted"}
