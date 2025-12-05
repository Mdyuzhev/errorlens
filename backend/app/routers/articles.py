"""Articles/Knowledge base CRUD router - thin controller."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.article_service import ArticleService


router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleCreate(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = []
    status: str = "draft"


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


@router.get("")
async def list_articles(
    category: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List articles with filters."""
    service = ArticleService(db)
    return await service.list_articles(
        category=category,
        status=status,
        tag=tag
    )


@router.get("/categories/list")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get unique categories."""
    service = ArticleService(db)
    return await service.get_categories()


@router.get("/{slug}")
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get article by slug (public for published)."""
    service = ArticleService(db)
    article = await service.get_article(slug)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return service.to_detail_dict(article)


@router.post("")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new article."""
    service = ArticleService(db)
    article = await service.create_article(
        title=data.title,
        content=data.content,
        author=user.username,
        excerpt=data.excerpt,
        category=data.category,
        tags=data.tags,
        status=data.status
    )
    return {"id": article.id, "slug": article.slug}


@router.put("/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update article."""
    service = ArticleService(db)
    article = await service.update_article(
        article_id,
        **data.model_dump(exclude_unset=True)
    )

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article updated"}


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete article."""
    service = ArticleService(db)
    deleted = await service.delete_article(article_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article deleted"}
