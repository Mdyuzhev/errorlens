"""Tests for TaskService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.task_service import VALID_PRIORITIES, VALID_STATUSES, TaskService


class TestTaskServiceConstants:
    """Tests for module-level constants."""

    def test_valid_statuses(self):
        """Test valid statuses for Kanban board."""
        assert VALID_STATUSES == ["todo", "in_progress", "review", "done"]

    def test_valid_priorities(self):
        """Test valid priority levels."""
        assert VALID_PRIORITIES == ["low", "medium", "high"]


class TestTaskService:
    """Tests for TaskService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        return db

    @pytest.fixture
    def mock_repo(self):
        """Create mock TaskRepository."""
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)
        repo.create = AsyncMock()
        repo.delete = AsyncMock(return_value=True)
        repo.list_with_filters = AsyncMock(return_value=[])
        repo.get_all_tasks = AsyncMock(return_value=[])
        repo.count_by_status = AsyncMock(return_value={})
        return repo

    @pytest.fixture
    def task_service(self, mock_db, mock_repo):
        """Create TaskService with mocked dependencies."""
        service = TaskService(mock_db)
        service.repo = mock_repo
        return service

    # ========== Create Task Tests ==========

    @pytest.mark.asyncio
    async def test_create_task_success(self, task_service, mock_repo):
        """Test creating task with valid data."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.title = "Test Task"
        mock_repo.create.return_value = mock_task

        # Act
        result = await task_service.create_task(title="Test Task", description="Test description")

        # Assert
        assert result.id == "task-123"
        assert result.title == "Test Task"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_defaults(self, task_service, mock_repo):
        """Test creating task uses default status and priority."""
        # Arrange
        mock_task = MagicMock()
        mock_repo.create.return_value = mock_task

        # Act
        await task_service.create_task(title="Test Task")

        # Assert
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["status"] == "todo"
        assert call_args["priority"] == "medium"
        assert call_args["labels"] == []

    @pytest.mark.asyncio
    async def test_create_task_invalid_status_defaults_to_todo(self, task_service, mock_repo):
        """Test invalid status gets reset to 'todo'."""
        # Arrange
        mock_task = MagicMock()
        mock_repo.create.return_value = mock_task

        # Act
        await task_service.create_task(title="Test Task", status="invalid_status")

        # Assert
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["status"] == "todo"

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority_defaults_to_medium(self, task_service, mock_repo):
        """Test invalid priority gets reset to 'medium'."""
        # Arrange
        mock_task = MagicMock()
        mock_repo.create.return_value = mock_task

        # Act
        await task_service.create_task(title="Test Task", priority="critical")  # invalid

        # Assert
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self, task_service, mock_repo):
        """Test creating task with all optional fields."""
        # Arrange
        mock_task = MagicMock()
        mock_repo.create.return_value = mock_task
        due_date = datetime(2025, 12, 31)

        # Act
        await task_service.create_task(
            title="Full Task",
            description="Full description",
            status="in_progress",
            priority="high",
            assignee="user@example.com",
            labels=["bug", "urgent"],
            due_date=due_date,
            session_id="session-123",
            testcase_id="tc-456",
        )

        # Assert
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["title"] == "Full Task"
        assert call_args["description"] == "Full description"
        assert call_args["status"] == "in_progress"
        assert call_args["priority"] == "high"
        assert call_args["assignee"] == "user@example.com"
        assert call_args["labels"] == ["bug", "urgent"]
        assert call_args["due_date"] == due_date
        assert call_args["session_id"] == "session-123"
        assert call_args["testcase_id"] == "tc-456"

    # ========== Get Task Tests ==========

    @pytest.mark.asyncio
    async def test_get_task_found(self, task_service, mock_repo):
        """Test getting existing task."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_repo.get_by_id.return_value = mock_task

        # Act
        result = await task_service.get_task("task-123")

        # Assert
        assert result == mock_task
        mock_repo.get_by_id.assert_called_once_with("task-123")

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_service, mock_repo):
        """Test getting non-existent task returns None."""
        # Arrange
        mock_repo.get_by_id.return_value = None

        # Act
        result = await task_service.get_task("nonexistent-id")

        # Assert
        assert result is None

    # ========== List Tasks Tests ==========

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, task_service, mock_repo):
        """Test listing tasks when none exist."""
        # Arrange
        mock_repo.list_with_filters.return_value = []

        # Act
        result = await task_service.list_tasks()

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, task_service, mock_repo):
        """Test listing tasks applies filters."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-1"
        mock_task.title = "Test Task"
        mock_task.description = "Description"
        mock_task.status = "todo"
        mock_task.priority = "high"
        mock_task.assignee = "user@example.com"
        mock_task.labels = ["bug"]
        mock_task.due_date = None
        mock_task.created_at = datetime(2025, 1, 15)
        mock_task.completed_at = None
        mock_repo.list_with_filters.return_value = [mock_task]

        # Act
        result = await task_service.list_tasks(
            status="todo", priority="high", assignee="user@example.com"
        )

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "task-1"
        mock_repo.list_with_filters.assert_called_once_with(
            status="todo", priority="high", assignee="user@example.com", session_id=None
        )

    # ========== Kanban Board Tests ==========

    @pytest.mark.asyncio
    async def test_get_board_empty(self, task_service, mock_repo):
        """Test getting empty Kanban board."""
        # Arrange
        mock_repo.get_all_tasks.return_value = []

        # Act
        result = await task_service.get_board()

        # Assert
        assert result == {"todo": [], "in_progress": [], "review": [], "done": []}

    @pytest.mark.asyncio
    async def test_get_board_groups_by_status(self, task_service, mock_repo):
        """Test tasks are grouped by status on board."""
        # Arrange
        task1 = MagicMock()
        task1.id = "task-1"
        task1.title = "Todo Task"
        task1.description = None
        task1.status = "todo"
        task1.priority = "medium"
        task1.assignee = None
        task1.labels = []
        task1.due_date = None
        task1.created_at = datetime(2025, 1, 15)
        task1.completed_at = None

        task2 = MagicMock()
        task2.id = "task-2"
        task2.title = "Done Task"
        task2.description = None
        task2.status = "done"
        task2.priority = "low"
        task2.assignee = None
        task2.labels = []
        task2.due_date = None
        task2.created_at = datetime(2025, 1, 14)
        task2.completed_at = datetime(2025, 1, 15)

        mock_repo.get_all_tasks.return_value = [task1, task2]

        # Act
        result = await task_service.get_board()

        # Assert
        assert len(result["todo"]) == 1
        assert len(result["done"]) == 1
        assert result["todo"][0]["id"] == "task-1"
        assert result["done"][0]["id"] == "task-2"

    # ========== Move Task Tests ==========

    @pytest.mark.asyncio
    async def test_move_task_success(self, task_service, mock_repo, mock_db):
        """Test moving task to valid status."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.status = "todo"
        mock_task.completed_at = None
        mock_repo.get_by_id.return_value = mock_task

        # Act
        result = await task_service.move_task("task-123", "in_progress")

        # Assert
        assert result == mock_task
        assert mock_task.status == "in_progress"

    @pytest.mark.asyncio
    async def test_move_task_invalid_status(self, task_service, mock_repo):
        """Test moving task to invalid status returns None."""
        # Act
        result = await task_service.move_task("task-123", "invalid")

        # Assert
        assert result is None
        mock_repo.get_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_move_task_to_done_sets_completed_at(self, task_service, mock_repo, mock_db):
        """Test moving task to done sets completed_at timestamp."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.status = "review"
        mock_task.completed_at = None
        mock_repo.get_by_id.return_value = mock_task

        # Act
        await task_service.move_task("task-123", "done")

        # Assert
        assert mock_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_move_task_from_done_clears_completed_at(self, task_service, mock_repo, mock_db):
        """Test moving task from done clears completed_at."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.status = "done"
        mock_task.completed_at = datetime(2025, 1, 15)
        mock_repo.get_by_id.return_value = mock_task

        # Act
        await task_service.move_task("task-123", "review")

        # Assert
        assert mock_task.completed_at is None

    # ========== Update Task Tests ==========

    @pytest.mark.asyncio
    async def test_update_task_success(self, task_service, mock_repo, mock_db):
        """Test updating task fields."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.title = "Original Title"
        mock_task.status = "todo"
        mock_task.completed_at = None
        mock_repo.get_by_id.return_value = mock_task

        # Act
        result = await task_service.update_task("task-123", title="Updated Title", priority="high")

        # Assert
        assert result == mock_task
        assert mock_task.title == "Updated Title"
        assert mock_task.priority == "high"
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, task_service, mock_repo):
        """Test updating non-existent task returns None."""
        # Arrange
        mock_repo.get_by_id.return_value = None

        # Act
        result = await task_service.update_task("nonexistent-id", title="New")

        # Assert
        assert result is None

    # ========== Delete Task Tests ==========

    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_service, mock_repo, mock_db):
        """Test deleting existing task."""
        # Arrange
        mock_repo.delete.return_value = True

        # Act
        result = await task_service.delete_task("task-123")

        # Assert
        assert result is True
        mock_repo.delete.assert_called_once_with("task-123")
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, task_service, mock_repo, mock_db):
        """Test deleting non-existent task returns False."""
        # Arrange
        mock_repo.delete.return_value = False

        # Act
        result = await task_service.delete_task("nonexistent-id")

        # Assert
        assert result is False

    # ========== Stats Tests ==========

    @pytest.mark.asyncio
    async def test_get_stats(self, task_service, mock_repo):
        """Test getting task statistics."""
        # Arrange
        mock_repo.count_by_status.return_value = {
            "todo": 5,
            "in_progress": 3,
            "review": 2,
            "done": 10,
        }

        # Act
        result = await task_service.get_stats()

        # Assert
        assert result["todo"] == 5
        assert result["in_progress"] == 3
        assert result["review"] == 2
        assert result["done"] == 10
        mock_repo.count_by_status.assert_called_once()

    # ========== Dict Conversion Tests ==========

    def test_to_list_dict(self, task_service):
        """Test task to list dict conversion."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.title = "Test Task"
        mock_task.description = "Description"
        mock_task.status = "todo"
        mock_task.priority = "high"
        mock_task.assignee = "user@example.com"
        mock_task.labels = ["bug", "urgent"]
        mock_task.due_date = datetime(2025, 12, 31)
        mock_task.created_at = datetime(2025, 1, 15)
        mock_task.completed_at = None

        # Act
        result = task_service._to_list_dict(mock_task)

        # Assert
        assert result["id"] == "task-123"
        assert result["title"] == "Test Task"
        assert result["due_date"] == "2025-12-31T00:00:00"
        assert result["completed_at"] is None

    def test_to_detail_dict(self, task_service):
        """Test task to detail dict includes session and testcase."""
        # Arrange
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_task.title = "Test Task"
        mock_task.description = "Description"
        mock_task.status = "todo"
        mock_task.priority = "high"
        mock_task.assignee = None
        mock_task.labels = []
        mock_task.due_date = None
        mock_task.created_at = datetime(2025, 1, 15)
        mock_task.completed_at = None
        mock_task.session_id = "session-123"
        mock_task.testcase_id = "tc-456"

        # Act
        result = task_service.to_detail_dict(mock_task)

        # Assert
        assert result["session_id"] == "session-123"
        assert result["testcase_id"] == "tc-456"
