"""Articles/Knowledge base CRUD router."""

import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.db_models import Article
from app.models.user import User

router = APIRouter(prefix="/articles", tags=["articles"])


def slugify(text: str) -> str:
    """Generate URL-friendly slug from title."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:200]


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
    query = select(Article).order_by(Article.created_at.desc())

    if category:
        query = query.where(Article.category == category)
    if status:
        query = query.where(Article.status == status)

    result = await db.execute(query)
    articles = result.scalars().all()

    # Filter by tag (JSON contains)
    if tag:
        articles = [a for a in articles if tag in (a.tags or [])]

    return [
        {
            "id": a.id,
            "title": a.title,
            "slug": a.slug,
            "excerpt": a.excerpt,
            "category": a.category,
            "tags": a.tags,
            "status": a.status,
            "author": a.author,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "views": a.views,
        }
        for a in articles
    ]


@router.get("/categories/list")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get unique categories."""
    result = await db.execute(
        select(Article.category).distinct().where(Article.category.isnot(None))
    )
    return [r[0] for r in result.all() if r[0]]


@router.get("/{slug}")
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get article by slug (public for published)."""
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment views
    article.views += 1
    await db.commit()

    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "content": article.content,
        "excerpt": article.excerpt,
        "category": article.category,
        "tags": article.tags,
        "status": article.status,
        "author": article.author,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "published_at": (
            article.published_at.isoformat() if article.published_at else None
        ),
        "views": article.views,
    }


@router.post("")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new article."""
    slug = slugify(data.title)

    # Ensure unique slug
    existing = await db.execute(select(Article).where(Article.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M')}"

    article = Article(
        title=data.title,
        slug=slug,
        content=data.content,
        excerpt=data.excerpt or data.content[:200],
        category=data.category,
        tags=data.tags,
        status=data.status,
        author=user.username,
        published_at=datetime.utcnow() if data.status == "published" else None,
    )

    db.add(article)
    await db.commit()
    await db.refresh(article)

    return {"id": article.id, "slug": article.slug}


@router.put("/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)

    # Set published_at when publishing
    if data.status == "published" and not article.published_at:
        article.published_at = datetime.utcnow()

    article.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Article updated"}


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete article."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    await db.delete(article)
    await db.commit()

    return {"message": "Article deleted"}
