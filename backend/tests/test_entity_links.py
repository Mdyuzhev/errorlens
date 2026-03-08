"""Tests for EntityLink service and repository."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.entity_link_service import EntityLinkService


def _make_entity_link(source_id, target_type, target_id, link_type="related"):
    """Helper to create a mock EntityLink."""
    el = MagicMock()
    el.source_id = source_id
    el.target_type = target_type
    el.target_id = target_id
    el.link_type = link_type
    return el


def _tiptap_doc_with_mentions(mentions: list[dict]) -> str:
    """Build a TipTap JSON document with entityMention nodes."""
    content = []
    for m in mentions:
        content.append({
            "type": "entityMention",
            "attrs": {
                "entityType": m.get("entityType", "testcase"),
                "entityId": m.get("entityId", "id-1"),
                "entityTitle": m.get("entityTitle", "Title"),
                "linkType": m.get("linkType", "related"),
            },
        })
    doc = {
        "type": "doc",
        "content": [{"type": "paragraph", "content": content}],
    }
    return json.dumps(doc)


class TestEntityLinkService:
    """Tests for EntityLinkService."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        svc = EntityLinkService(mock_db)
        svc.repo = AsyncMock()
        return svc

    # --- upsert_links ---

    @pytest.mark.asyncio
    async def test_upsert_links_creates(self, service):
        """New links are created."""
        service.repo.get_outgoing = AsyncMock(return_value=[])
        new_link = _make_entity_link("a1", "testcase", "tc1")
        service.repo.upsert_links = AsyncMock(return_value=[new_link])

        result = await service.repo.upsert_links(
            "a1",
            [{"target_type": "testcase", "target_id": "tc1", "link_type": "related"}],
        )

        assert len(result) == 1
        assert result[0].target_type == "testcase"
        service.repo.upsert_links.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_links_removes_stale(self, service):
        """Stale links removed when not in desired set."""
        # Repo returns empty after upsert (stale link removed)
        service.repo.upsert_links = AsyncMock(return_value=[])

        result = await service.repo.upsert_links("a1", [])

        assert result == []
        service.repo.upsert_links.assert_called_once_with("a1", [])

    @pytest.mark.asyncio
    async def test_upsert_links_idempotent(self, service):
        """Repeated upsert with same data doesn't duplicate."""
        existing = _make_entity_link("a1", "testcase", "tc1")
        service.repo.upsert_links = AsyncMock(return_value=[existing])

        links_data = [{"target_type": "testcase", "target_id": "tc1", "link_type": "related"}]
        result1 = await service.repo.upsert_links("a1", links_data)
        result2 = await service.repo.upsert_links("a1", links_data)

        assert len(result1) == 1
        assert len(result2) == 1

    # --- get_incoming / backlinks ---

    @pytest.mark.asyncio
    async def test_get_incoming_returns_backlinks(self, service):
        """Backlinks returned correctly."""
        link = _make_entity_link("a1", "testcase", "tc1")
        service.repo.get_incoming = AsyncMock(return_value=[link])

        mock_article = MagicMock()
        mock_article.id = "a1"
        mock_article.title = "Article One"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_article]
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_backlinks("testcase", "tc1")

        assert len(result) == 1
        assert result[0]["article_id"] == "a1"
        assert result[0]["article_title"] == "Article One"

    # --- preview ---

    @pytest.mark.asyncio
    async def test_preview_article(self, service):
        """Preview returns article title and status."""
        mock_article = MagicMock()
        mock_article.id = "a1"
        mock_article.title = "Test Article"
        mock_article.status = "published"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_article
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_entity_preview("article", "a1")

        assert result is not None
        assert result["title"] == "Test Article"
        assert result["type"] == "article"
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_preview_testcase(self, service):
        """Preview returns testcase title and status."""
        mock_tc = MagicMock()
        mock_tc.id = "tc1"
        mock_tc.title = "Login Test"
        mock_tc.status = "Draft"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tc
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_entity_preview("testcase", "tc1")

        assert result is not None
        assert result["title"] == "Login Test"
        assert result["type"] == "testcase"

    @pytest.mark.asyncio
    async def test_preview_task(self, service):
        """Preview returns task title and status."""
        mock_task = MagicMock()
        mock_task.id = "t1"
        mock_task.title = "Fix Bug"
        mock_task.status = "in_progress"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_entity_preview("task", "t1")

        assert result is not None
        assert result["title"] == "Fix Bug"
        assert result["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_preview_invalid_type(self, service):
        """Invalid entity type returns None."""
        result = await service.get_entity_preview("unknown_type", "id-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_preview_not_found(self, service):
        """Non-existent entity returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_entity_preview("article", "nonexistent-id")
        assert result is None

    # --- sync_links_from_document ---

    @pytest.mark.asyncio
    async def test_sync_extracts_mentions(self, service):
        """sync_links_from_document extracts entityMention nodes from TipTap JSON."""
        service.repo.upsert_links = AsyncMock(return_value=[])

        doc = _tiptap_doc_with_mentions([
            {"entityType": "testcase", "entityId": "tc-1", "linkType": "verifies"},
            {"entityType": "task", "entityId": "task-2", "linkType": "related"},
        ])

        await service.sync_links_from_document("article-1", doc, "org-1")

        service.repo.upsert_links.assert_called_once()
        call_args = service.repo.upsert_links.call_args
        links = call_args[0][1]
        assert len(links) == 2
        assert links[0]["target_type"] == "testcase"
        assert links[0]["target_id"] == "tc-1"
        assert links[0]["link_type"] == "verifies"
        assert links[1]["target_type"] == "task"
        assert links[1]["target_id"] == "task-2"

    @pytest.mark.asyncio
    async def test_sync_empty_content(self, service):
        """Empty content clears all links."""
        service.repo.upsert_links = AsyncMock(return_value=[])

        await service.sync_links_from_document("article-1", None)

        service.repo.upsert_links.assert_called_once_with("article-1", [])

    @pytest.mark.asyncio
    async def test_sync_invalid_json(self, service):
        """Invalid JSON returns empty list without error."""
        result = await service.sync_links_from_document("article-1", "not-json{{{")
        assert result == []

    @pytest.mark.asyncio
    async def test_sync_nested_mentions(self, service):
        """Mentions nested in blockquote/list are extracted."""
        service.repo.upsert_links = AsyncMock(return_value=[])

        doc = json.dumps({
            "type": "doc",
            "content": [
                {
                    "type": "blockquote",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "entityMention",
                                    "attrs": {
                                        "entityType": "article",
                                        "entityId": "nested-1",
                                        "linkType": "related",
                                    },
                                }
                            ],
                        }
                    ],
                }
            ],
        })

        await service.sync_links_from_document("article-1", doc, "org-1")

        links = service.repo.upsert_links.call_args[0][1]
        assert len(links) == 1
        assert links[0]["target_id"] == "nested-1"
