"""Entity link service — business logic for entity mentions."""

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article, EntityLink, Task, TestCase
from app.repositories.entity_link_repo import EntityLinkRepository

logger = logging.getLogger(__name__)


class EntityLinkService:
    """Business logic for entity links (mentions)."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityLinkRepository(db)

    async def sync_links_from_document(
        self,
        article_id: str,
        content_json: str | None,
        org_id: str | None = None,
    ) -> list[EntityLink]:
        """Extract entityMention nodes from TipTap JSON and sync links."""
        if not content_json:
            return await self.repo.upsert_links(article_id, [])

        try:
            doc = json.loads(content_json) if isinstance(content_json, str) else content_json
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse content JSON for article %s", article_id)
            return []

        mentions = self._extract_mentions(doc)
        links = [
            {
                "target_type": m["entityType"],
                "target_id": m["entityId"],
                "link_type": m.get("linkType", "related"),
            }
            for m in mentions
            if m.get("entityType") and m.get("entityId")
        ]

        return await self.repo.upsert_links(article_id, links, org_id)

    def _extract_mentions(self, node: dict) -> list[dict]:
        """Recursively extract entityMention nodes from TipTap JSON."""
        mentions: list[dict] = []
        if node.get("type") == "entityMention":
            attrs = node.get("attrs", {})
            mentions.append(attrs)
        for child in node.get("content", []):
            mentions.extend(self._extract_mentions(child))
        return mentions

    async def get_entity_preview(
        self, entity_type: str, entity_id: str
    ) -> dict[str, Any] | None:
        """Get preview data for an entity (title, status)."""
        if entity_type == "article":
            result = await self.db.execute(
                select(Article).where(Article.id == entity_id)
            )
            article = result.scalar_one_or_none()
            if not article:
                return None
            return {
                "id": article.id,
                "type": "article",
                "title": article.title,
                "status": article.status,
                "slug": article.slug,
                "human_id": article.human_id,
            }

        if entity_type == "testcase":
            result = await self.db.execute(
                select(TestCase).where(TestCase.id == entity_id)
            )
            tc = result.scalar_one_or_none()
            if not tc:
                return None
            return {
                "id": tc.id,
                "type": "testcase",
                "title": tc.title,
                "status": tc.status,
                "human_id": tc.human_id,
            }

        if entity_type == "task":
            result = await self.db.execute(
                select(Task).where(Task.id == entity_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return None
            return {
                "id": task.id,
                "type": "task",
                "title": task.title,
                "status": task.status,
                "human_id": task.human_id,
            }

        return None

    async def get_backlinks(
        self, target_type: str, target_id: str
    ) -> list[dict[str, Any]]:
        """Get articles that reference this entity."""
        links = await self.repo.get_incoming(target_type, target_id)
        if not links:
            return []

        source_ids = [link.source_id for link in links]
        result = await self.db.execute(
            select(Article).where(Article.id.in_(source_ids))
        )
        articles = {a.id: a for a in result.scalars().all()}

        return [
            {
                "article_id": link.source_id,
                "article_title": articles[link.source_id].title
                if link.source_id in articles
                else "Deleted article",
            }
            for link in links
        ]
