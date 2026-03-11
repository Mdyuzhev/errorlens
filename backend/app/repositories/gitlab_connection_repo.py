"""Repository for GitLab connections."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import GitLabConnection
from app.repositories.base import BaseRepository


class GitLabConnectionRepository(BaseRepository[GitLabConnection]):
    """Data access for GitLab connections."""

    def __init__(self, db: AsyncSession):
        super().__init__(GitLabConnection, db)

    async def get_by_org(self, org_id: str, active_only: bool = True) -> list[GitLabConnection]:
        """Get connections for an organization (project)."""
        query = select(GitLabConnection).where(GitLabConnection.organization_id == org_id)
        if active_only:
            query = query.where(GitLabConnection.is_active.is_(True))
        query = query.order_by(GitLabConnection.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_check_status(self, connection_id: str, ok: bool) -> None:
        """Update last check timestamp and result."""
        conn = await self.get_by_id(connection_id)
        if conn:
            conn.last_checked_at = datetime.utcnow()
            conn.last_check_ok = ok
            await self.session.flush()
