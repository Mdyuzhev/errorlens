"""Article service - business logic layer."""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article
from app.repositories.article_repo import ArticleRepository


def slugify(text: str) -> str:
    """Generate URL-friendly slug from title."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:200]


class ArticleService:
    """Service for article business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ArticleRepository(db)

    async def create_article(
        self,
        title: str,
        content: str,
        author: str,
        excerpt: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        status: str = "draft"
    ) -> Article:
        """Create new article with unique slug."""
        slug = slugify(title)

        # Ensure unique slug
        existing = await self.repo.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M')}"

        article_data = {
            "title": title,
            "slug": slug,
            "content": content,
            "excerpt": excerpt or content[:200],
            "category": category,
            "tags": tags or [],
            "status": status,
            "author": author,
            "published_at": datetime.utcnow() if status == "published" else None,
        }

        article = await self.repo.create(article_data)
        await self.db.commit()
        return article

    async def get_article(self, slug: str, increment_views: bool = True) -> Optional[Article]:
        """Get article by slug."""
        article = await self.repo.get_by_slug(slug)
        if article and increment_views:
            await self.repo.increment_views(article)
            await self.db.commit()
        return article

    async def get_article_by_id(self, article_id: str) -> Optional[Article]:
        """Get article by ID."""
        return await self.repo.get_by_id(article_id)

    async def list_articles(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List articles with filters."""
        articles = await self.repo.list_with_filters(
            category=category,
            status=status,
            limit=limit,
            offset=offset
        )

        # Filter by tag (post-filter for JSON field)
        if tag:
            articles = [a for a in articles if tag in (a.tags or [])]

        return [self._to_list_dict(a) for a in articles]

    async def get_categories(self) -> List[str]:
        """Get unique categories."""
        return await self.repo.get_categories()

    async def update_article(
        self,
        article_id: str,
        **updates
    ) -> Optional[Article]:
        """Update article fields."""
        article = await self.repo.get_by_id(article_id)
        if not article:
            return None

        for key, value in updates.items():
            if value is not None:
                setattr(article, key, value)

        # Set published_at when publishing
        if updates.get("status") == "published" and not article.published_at:
            article.published_at = datetime.utcnow()

        article.updated_at = datetime.utcnow()
        await self.db.commit()
        return article

    async def delete_article(self, article_id: str) -> bool:
        """Delete article by ID."""
        deleted = await self.repo.delete(article_id)
        if deleted:
            await self.db.commit()
        return deleted

    def _to_list_dict(self, article: Article) -> Dict[str, Any]:
        """Convert article to list response dict."""
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "category": article.category,
            "tags": article.tags,
            "status": article.status,
            "author": article.author,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "views": article.views,
        }

    def to_detail_dict(self, article: Article) -> Dict[str, Any]:
        """Convert article to detailed response dict."""
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
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "views": article.views,
        }
