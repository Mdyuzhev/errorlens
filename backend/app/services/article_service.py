"""Article service - business logic layer."""

import re
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article, ArticleFolder
from app.repositories.article_repo import ArticleRepository
from app.services.entity_link_service import EntityLinkService
from app.services.project_service import ProjectService


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
        self.entity_link_service = EntityLinkService(db)

    async def create_article(
        self,
        title: str,
        content: str,
        author: str,
        excerpt: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        status: str = "draft",
        project_id: str | None = None,
        created_by: str | None = None,
        folder_id: str | None = None,
    ) -> Article:
        """Create new article with unique slug."""
        slug = slugify(title)

        # Ensure unique slug within project
        existing = await self.repo.get_by_slug(slug, project_id=project_id)
        if existing:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M')}"

        # Validate folder_id exists if provided
        if folder_id:
            folder_result = await self.db.execute(
                select(ArticleFolder).where(ArticleFolder.id == folder_id)
            )
            if not folder_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"Folder not found: {folder_id}")

        article_data = {
            "title": title,
            "slug": slug,
            "content": content,
            "excerpt": excerpt or content[:200],
            "category": category,
            "tags": tags or [],
            "status": status,
            "author": author,
            "project_id": project_id,
            "created_by": created_by,
            "folder_id": folder_id,
            "published_at": datetime.utcnow() if status == "published" else None,
        }

        # Generate human_id if project has a key
        if project_id:
            project_service = ProjectService(self.db)
            human_id = await project_service.next_human_id(project_id)
            if human_id:
                article_data["human_id"] = human_id

        article = await self.repo.create(article_data)
        await self.db.commit()
        return article

    async def get_article(
        self, slug: str, project_id: str | None = None, increment_views: bool = True
    ) -> Article | None:
        """Get article by slug."""
        article = await self.repo.get_by_slug(slug, project_id=project_id)
        if article and increment_views:
            await self.repo.increment_views(article)
            await self.db.commit()
        return article

    async def get_article_by_id(self, article_id: str) -> Article | None:
        """Get article by ID."""
        return await self.repo.get_by_id(article_id)

    async def list_articles(
        self,
        project_id: str | None = None,
        category: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        folder_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List articles with filters."""
        articles = await self.repo.list_with_filters(
            project_id=project_id,
            category=category,
            status=status,
            folder_id=folder_id,
            limit=limit,
            offset=offset,
        )

        # Filter by tag (post-filter for JSON field)
        if tag:
            articles = [a for a in articles if tag in (a.tags or [])]

        return [self._to_list_dict(a) for a in articles]

    async def search_articles(
        self,
        q: str,
        project_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search articles by title or content (ILIKE)."""
        articles = await self.repo.search(q, project_id=project_id, limit=limit)
        return [self._to_list_dict(a) for a in articles]

    async def get_categories(self, project_id: str | None = None) -> list[str]:
        """Get unique categories for a project."""
        return await self.repo.get_categories(project_id=project_id)

    async def update_article(self, article_id: str, **updates) -> Article | None:
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

        # Sync entity links if content was updated
        if "content" in updates and updates["content"]:
            await self.entity_link_service.sync_links_from_document(
                article_id=article.id,
                content_json=updates["content"],
            )

        await self.db.commit()
        return article

    async def delete_article(self, article_id: str) -> bool:
        """Delete article by ID."""
        deleted = await self.repo.delete(article_id)
        if deleted:
            await self.db.commit()
        return deleted

    def _to_list_dict(self, article: Article) -> dict[str, Any]:
        """Convert article to list response dict."""
        return {
            "id": article.id,
            "human_id": article.human_id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "category": article.category,
            "tags": article.tags,
            "status": article.status,
            "author": article.author,
            "project_id": article.project_id,
            "folder_id": article.folder_id,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "views": article.views,
        }

    def to_detail_dict(self, article: Article) -> dict[str, Any]:
        """Convert article to detailed response dict."""
        return {
            "id": article.id,
            "human_id": article.human_id,
            "title": article.title,
            "slug": article.slug,
            "content": article.content,
            "excerpt": article.excerpt,
            "category": article.category,
            "tags": article.tags,
            "status": article.status,
            "author": article.author,
            "project_id": article.project_id,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "views": article.views,
        }
