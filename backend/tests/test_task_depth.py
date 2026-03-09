"""Tests for task depth hierarchy."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.task_service import MAX_TASK_DEPTH, TaskService


class TestTaskDepth:
    """Tests for task hierarchy depth validation."""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def task_service(self, mock_db):
        service = TaskService(mock_db)
        service.repo = AsyncMock()
        return service

    def test_max_depth_constant(self):
        """Test maximum depth is 4."""
        assert MAX_TASK_DEPTH == 4

    @pytest.mark.asyncio
    async def test_parent_child(self, task_service, mock_db):
        """Test creating subtask with parent_id."""
        mock_task = MagicMock()
        mock_task.id = "task-child"
        mock_task.human_id = None
        mock_task.title = "Child task"
        mock_task.project_id = None
        task_service.repo.create = AsyncMock(return_value=mock_task)

        # Mock depth check: parent is at depth 1
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.task_service.event_publisher") as mock_pub:
            mock_pub.publish = AsyncMock()
            result = await task_service.create_task(
                title="Child task",
                parent_id="task-parent",
            )

        assert result.id == "task-child"
        task_service.repo.create.assert_called_once()
        create_data = task_service.repo.create.call_args[0][0]
        assert create_data["parent_id"] == "task-parent"

    @pytest.mark.asyncio
    async def test_max_depth(self, task_service, mock_db):
        """Test that creating subtask at depth 5+ raises 400."""
        from fastapi import HTTPException

        # Mock depth check: parent is at depth 4 (max)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 4
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await task_service.create_task(
                title="Too deep",
                parent_id="task-deep-parent",
            )
        assert exc.value.status_code == 400
        assert "depth" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_children(self, task_service):
        """Test GET /{id}/children returns direct children."""
        mock_child1 = MagicMock()
        mock_child1.id = "child-1"
        mock_child1.human_id = "EL-2"
        mock_child1.title = "Child 1"
        mock_child1.description = None
        mock_child1.status = "todo"
        mock_child1.priority = "medium"
        mock_child1.assignee = None
        mock_child1.labels = []
        mock_child1.due_date = None
        mock_child1.created_at = None
        mock_child1.completed_at = None
        mock_child1.type_id = None
        mock_child1.status_id = None
        mock_child1.assignee_id = None
        mock_child1.reporter_id = None
        mock_child1.severity = None
        mock_child1.environment = None
        mock_child1.estimated_hours = None
        mock_child1.spent_hours = None
        mock_child1.parent_id = "parent-1"
        mock_child1.task_type = None
        mock_child1.task_status = None
        mock_child1.assignee_user = None
        mock_child1.reporter = None

        task_service.repo.get_children = AsyncMock(return_value=[mock_child1])

        result = await task_service.get_children("parent-1")

        assert len(result) == 1
        assert result[0]["id"] == "child-1"
        assert result[0]["parent_id"] == "parent-1"
        task_service.repo.get_children.assert_called_once_with("parent-1")

    @pytest.mark.asyncio
    async def test_create_without_parent(self, task_service, mock_db):
        """Test creating task without parent_id skips depth check."""
        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.human_id = None
        mock_task.title = "No parent"
        mock_task.project_id = None
        task_service.repo.create = AsyncMock(return_value=mock_task)

        with patch("app.services.task_service.event_publisher") as mock_pub:
            mock_pub.publish = AsyncMock()
            result = await task_service.create_task(title="No parent")

        assert result.id == "task-1"
        # db.execute should not be called for depth check
        mock_db.execute.assert_not_called()
