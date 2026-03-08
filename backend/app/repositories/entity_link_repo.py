"""Repository for EntityLink CRUD operations."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import EntityLink


class EntityLinkRepository:
    """Data access for entity_links table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_links(
        self,
        source_id: str,
        links: list[dict],
        org_id: str | None = None,
    ) -> list[EntityLink]:
        """Sync links for a source article: add new, remove stale. Atomic."""
        # Current links in DB
        existing = await self.get_outgoing(source_id)
        existing_set = {
            (el.target_type, el.target_id) for el in existing
        }

        # Desired links from document
        desired_set = {
            (link["target_type"], link["target_id"]) for link in links
        }
        desired_map = {
            (link["target_type"], link["target_id"]): link for link in links
        }

        # Delete stale
        to_delete = existing_set - desired_set
        if to_delete:
            for target_type, target_id in to_delete:
                stmt = delete(EntityLink).where(
                    EntityLink.source_id == source_id,
                    EntityLink.target_type == target_type,
                    EntityLink.target_id == target_id,
                )
                await self.session.execute(stmt)

        # Add new
        to_add = desired_set - existing_set
        new_links: list[EntityLink] = []
        for target_type, target_id in to_add:
            link_data = desired_map[(target_type, target_id)]
            entity = EntityLink(
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                link_type=link_data.get("link_type", "related"),
            )
            self.session.add(entity)
            new_links.append(entity)

        await self.session.flush()

        # Return current state
        return await self.get_outgoing(source_id)

    async def get_outgoing(self, source_id: str) -> list[EntityLink]:
        """Get all links from a source article."""
        result = await self.session.execute(
            select(EntityLink).where(EntityLink.source_id == source_id)
        )
        return list(result.scalars().all())

    async def get_incoming(
        self, target_type: str, target_id: str
    ) -> list[EntityLink]:
        """Get backlinks to a target entity."""
        result = await self.session.execute(
            select(EntityLink).where(
                EntityLink.target_type == target_type,
                EntityLink.target_id == target_id,
            )
        )
        return list(result.scalars().all())

    async def delete_by_source(self, source_id: str) -> int:
        """Delete all links from a source article."""
        result = await self.session.execute(
            delete(EntityLink).where(EntityLink.source_id == source_id)
        )
        await self.session.flush()
        return result.rowcount
