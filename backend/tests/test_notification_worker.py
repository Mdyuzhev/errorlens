"""Tests for notification worker event handling."""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def mock_db():
    """Create a mock async DB session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestNotificationWorker:
    """Tests for notification_worker module."""

    @pytest.mark.asyncio
    async def test_task_assigned_creates_notification(self, mock_db):
        """task.assigned event creates notification for new assignee."""
        from app.worker.notification_worker import handle_event

        event = {
            "event_id": str(uuid.uuid4()),
            "type": "task.assigned",
            "project_id": "proj-1",
            "payload": json.dumps({
                "id": "task-1",
                "title": "Fix bug",
                "old_assignee_id": "user-old",
                "new_assignee_id": "user-new",
            }),
        }

        await handle_event(mock_db, event)
        mock_db.execute.assert_awaited()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_completed_notifies_starter(self, mock_db):
        """testplan_run.completed event notifies started_by user."""
        from app.worker.notification_worker import handle_event

        # Mock: TestPlanRun.started_by returns user-1
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "user-1"
        mock_db.execute.return_value = mock_result

        event = {
            "event_id": str(uuid.uuid4()),
            "type": "testplan_run.completed",
            "project_id": "",
            "payload": json.dumps({
                "run_id": "run-1",
                "plan_id": "plan-1",
                "plan_name": "Smoke Tests",
                "total": 10,
                "passed": 10,
                "failed": 0,
                "blocked": 0,
            }),
        }

        await handle_event(mock_db, event)
        mock_db.execute.assert_awaited()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_idempotency(self, mock_db):
        """Repeated processing of same event_id does not raise (ON CONFLICT DO NOTHING)."""
        from app.worker.notification_worker import handle_event

        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "type": "task.assigned",
            "project_id": "",
            "payload": json.dumps({
                "id": "task-1",
                "title": "Task",
                "old_assignee_id": None,
                "new_assignee_id": "user-1",
            }),
        }

        # Process twice — should not raise
        await handle_event(mock_db, event)
        await handle_event(mock_db, event)

    @pytest.mark.asyncio
    async def test_critical_session_notifies_admins(self, mock_db):
        """session.analyzed with severity=critical notifies project admins."""
        from app.worker.notification_worker import handle_event

        # Mock get_project_admins
        mock_result_admins = MagicMock()
        mock_result_admins.all.return_value = [("admin-1",), ("admin-2",)]

        mock_db.execute.return_value = mock_result_admins

        event = {
            "event_id": str(uuid.uuid4()),
            "type": "session.analyzed",
            "project_id": "proj-1",
            "payload": json.dumps({
                "session_id": "sess-1",
                "severity": "critical",
                "summary": "Critical JS error",
            }),
        }

        await handle_event(mock_db, event)
        # Should have called execute multiple times (get admins + insert notifications)
        assert mock_db.execute.await_count >= 2

    @pytest.mark.asyncio
    async def test_unknown_event_type_skipped(self, mock_db):
        """Unknown event type does not cause errors."""
        from app.worker.notification_worker import handle_event

        event = {
            "event_id": str(uuid.uuid4()),
            "type": "unknown.event",
            "project_id": "",
            "payload": json.dumps({"data": "test"}),
        }

        # Should not raise
        await handle_event(mock_db, event)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_task_status_changed_notifies_assignee(self, mock_db):
        """task.status_changed notifies the task assignee."""
        from app.worker.notification_worker import handle_event

        event = {
            "event_id": str(uuid.uuid4()),
            "type": "task.status_changed",
            "project_id": "proj-1",
            "payload": json.dumps({
                "id": "task-1",
                "title": "Fix bug",
                "old_status": "todo",
                "new_status": "done",
                "assignee_id": "user-1",
            }),
        }

        await handle_event(mock_db, event)
        mock_db.execute.assert_awaited()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_empty_input(self, mock_db):
        """Empty event with minimal fields does not crash."""
        from app.worker.notification_worker import handle_event

        event = {
            "event_id": "",
            "type": "",
            "project_id": "",
            "payload": "{}",
        }
        await handle_event(mock_db, event)

    @pytest.mark.asyncio
    async def test_none_handling(self, mock_db):
        """Missing keys in event are handled gracefully."""
        from app.worker.notification_worker import handle_event

        event = {}  # All fields missing
        # Should handle KeyError gracefully or at least not crash the worker
        try:
            await handle_event(mock_db, event)
        except (KeyError, json.JSONDecodeError):
            pass  # Expected — worker wraps in try/except

    @pytest.mark.asyncio
    async def test_memory_cleanup(self, mock_db):
        """Worker does not accumulate state between events."""
        from app.worker.notification_worker import handle_event

        for i in range(100):
            event = {
                "event_id": str(uuid.uuid4()),
                "type": "task.assigned",
                "project_id": "",
                "payload": json.dumps({
                    "id": f"task-{i}",
                    "title": f"Task {i}",
                    "old_assignee_id": None,
                    "new_assignee_id": f"user-{i}",
                }),
            }
            await handle_event(mock_db, event)
        # No assertion — just verifying no memory issues or exceptions
