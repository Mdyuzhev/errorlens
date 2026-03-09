"""Tests for task relations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.task_relation_service import (
    INVERSE_TYPES,
    VALID_RELATION_TYPES,
    TaskRelationService,
)


class TestTaskRelations:
    """Tests for TaskRelationService."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def relation_service(self, mock_db):
        return TaskRelationService(mock_db)

    def test_inverse_types_mapping(self):
        """Test that all relation types have inverse mappings."""
        assert INVERSE_TYPES["blocks"] == "blocked_by"
        assert INVERSE_TYPES["blocked_by"] == "blocks"
        assert INVERSE_TYPES["duplicates"] == "duplicated_by"
        assert INVERSE_TYPES["duplicated_by"] == "duplicates"
        assert INVERSE_TYPES["relates_to"] == "relates_to"

    def test_valid_relation_types(self):
        """Test valid relation types set."""
        assert "blocks" in VALID_RELATION_TYPES
        assert "blocked_by" in VALID_RELATION_TYPES
        assert "relates_to" in VALID_RELATION_TYPES
        assert "duplicates" in VALID_RELATION_TYPES
        assert "invalid" not in VALID_RELATION_TYPES

    @pytest.mark.asyncio
    async def test_create_blocks(self, relation_service, mock_db):
        """Test creating blocks relation creates both forward and inverse."""
        # Mock: no existing relation
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.all.return_value = []  # no cycle
        mock_db.execute.return_value = mock_result

        relation = await relation_service.create_relation(
            "task-A", "task-B", "blocks", "user-1"
        )

        # Should call db.add twice (forward + inverse)
        assert mock_db.add.call_count == 2

        # First call: forward (A blocks B)
        forward = mock_db.add.call_args_list[0][0][0]
        assert forward.source_task_id == "task-A"
        assert forward.target_task_id == "task-B"
        assert forward.relation_type == "blocks"

        # Second call: inverse (B blocked_by A)
        inverse = mock_db.add.call_args_list[1][0][0]
        assert inverse.source_task_id == "task-B"
        assert inverse.target_task_id == "task-A"
        assert inverse.relation_type == "blocked_by"

    @pytest.mark.asyncio
    async def test_delete_blocks(self, relation_service, mock_db):
        """Test deleting blocks relation removes both records."""
        mock_relation = MagicMock()
        mock_relation.id = "rel-1"
        mock_relation.source_task_id = "task-A"
        mock_relation.target_task_id = "task-B"
        mock_relation.relation_type = "blocks"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_relation
        mock_db.execute.return_value = mock_result

        result = await relation_service.delete_relation("rel-1")
        assert result is True
        # Should execute delete queries for both directions
        assert mock_db.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_cyclic_blocks(self, relation_service, mock_db):
        """Test that A blocks B + B blocks A is rejected."""
        from fastapi import HTTPException

        # First call: check existing — none
        # Second call: BFS finds cycle
        call_count = 0

        async def mock_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                # No existing relation
                mock_result.scalar_one_or_none.return_value = None
            elif call_count == 2:
                # BFS: task-B blocks task-A (cycle!)
                mock_result.all.return_value = [("task-A",)]
            return mock_result

        mock_db.execute = mock_execute

        with pytest.raises(HTTPException) as exc:
            await relation_service.create_relation("task-A", "task-B", "blocks")
        assert exc.value.status_code == 400
        assert "Cyclic" in exc.value.detail

    @pytest.mark.asyncio
    async def test_relates_to_symmetric(self, relation_service, mock_db):
        """Test relates_to creates symmetric pair."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        await relation_service.create_relation("task-A", "task-B", "relates_to")

        assert mock_db.add.call_count == 2
        forward = mock_db.add.call_args_list[0][0][0]
        inverse = mock_db.add.call_args_list[1][0][0]
        assert forward.relation_type == "relates_to"
        assert inverse.relation_type == "relates_to"

    @pytest.mark.asyncio
    async def test_duplicate_relation(self, relation_service, mock_db):
        """Test that creating duplicate relation returns 400."""
        from fastapi import HTTPException

        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await relation_service.create_relation("task-A", "task-B", "blocks")
        assert exc.value.status_code == 400
        assert "already exists" in exc.value.detail

    @pytest.mark.asyncio
    async def test_self_relation_rejected(self, relation_service, mock_db):
        """Test that relating task to itself is rejected."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await relation_service.create_relation("task-A", "task-A", "blocks")
        assert exc.value.status_code == 400
        assert "itself" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_relation_type(self, relation_service, mock_db):
        """Test that invalid relation type is rejected."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await relation_service.create_relation("task-A", "task-B", "invalid_type")
        assert exc.value.status_code == 400
        assert "Invalid" in exc.value.detail
