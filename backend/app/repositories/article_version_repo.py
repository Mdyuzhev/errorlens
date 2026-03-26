"""Article version repository - data access layer for version snapshots."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleVersion
from app.repositories.base import BaseRepository


class ArticleVersionRepository(BaseRepository[ArticleVersion]):
    """Repository for ArticleVersion CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ArticleVersion, db)

    async def create_version(
        self,
        article_id: str,
        title: str,
        content: str,
        saved_by: str | None = None,
    ) -> ArticleVersion:
        """Create a new version snapshot for an article."""
        instance = ArticleVersion(
            article_id=article_id,
            title=title,
            content=content,
            saved_by=saved_by,
        )
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def list_by_article(self, article_id: str) -> list[ArticleVersion]:
        """List all versions for an article, newest first."""
        query = (
            select(ArticleVersion)
            .where(ArticleVersion.article_id == article_id)
            .order_by(ArticleVersion.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id_and_article(
        self, version_id: str, article_id: str
    ) -> ArticleVersion | None:
        """Get a specific version ensuring it belongs to the given article."""
        query = select(ArticleVersion).where(
            ArticleVersion.id == version_id,
            ArticleVersion.article_id == article_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_oldest_if_limit(
        self, article_id: str, limit: int = 50
    ) -> int:
        """Delete oldest versions if count exceeds limit. Returns deleted count."""
        query = (
            select(ArticleVersion)
            .where(ArticleVersion.article_id == article_id)
            .order_by(ArticleVersion.created_at.asc())
        )
        result = await self.session.execute(query)
        versions = list(result.scalars().all())

        overflow = len(versions) - limit
        if overflow <= 0:
            return 0

        ids_to_delete = [v.id for v in versions[:overflow]]
        return await self.bulk_delete(ids_to_delete)
