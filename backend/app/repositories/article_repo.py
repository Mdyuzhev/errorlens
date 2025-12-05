"""Article repository - data access layer."""

from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    """Repository for Article CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Article, db)

    async def get_by_slug(self, slug: str) -> Optional[Article]:
        """Get article by slug."""
        result = await self.session.execute(
            select(Article).where(Article.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Article]:
        """List articles with filters."""
        query = select(Article).order_by(Article.created_at.desc())

        if category:
            query = query.where(Article.category == category)
        if status:
            query = query.where(Article.status == status)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_categories(self) -> List[str]:
        """Get unique categories."""
        result = await self.session.execute(
            select(Article.category).distinct().where(Article.category.isnot(None))
        )
        return [r[0] for r in result.all() if r[0]]

    async def increment_views(self, article: Article) -> None:
        """Increment article view counter."""
        article.views += 1
        await self.session.flush()
