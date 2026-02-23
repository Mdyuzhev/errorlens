"""Article repository - data access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    """Repository for Article CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Article, db)

    async def get_by_slug(self, slug: str, project_id: str | None = None) -> Article | None:
        """Get article by slug, optionally filtered by project."""
        query = select(Article).where(Article.slug == slug)
        if project_id:
            query = query.where(Article.project_id == project_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        project_id: str | None = None,
        category: str | None = None,
        status: str | None = None,
        folder_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Article]:
        """List articles with filters including project_id and folder_id."""
        query = select(Article).order_by(Article.created_at.desc())

        # Filter by project_id for multi-tenancy
        if project_id:
            query = query.where(Article.project_id == project_id)

        if category:
            query = query.where(Article.category == category)
        if status:
            query = query.where(Article.status == status)
        if folder_id is not None:
            if folder_id == "root":
                query = query.where(Article.folder_id.is_(None))
            else:
                query = query.where(Article.folder_id == folder_id)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_categories(self, project_id: str | None = None) -> list[str]:
        """Get unique categories, optionally filtered by project."""
        query = select(Article.category).distinct().where(Article.category.isnot(None))
        if project_id:
            query = query.where(Article.project_id == project_id)
        result = await self.session.execute(query)
        return [r[0] for r in result.all() if r[0]]

    async def increment_views(self, article: Article) -> None:
        """Increment article view counter."""
        article.views += 1
        await self.session.flush()
