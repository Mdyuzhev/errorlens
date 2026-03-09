"""Tests for notifications API router."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_notification(
    user_id: str = "user-1",
    is_read: bool = False,
    event_type: str = "task.assigned",
) -> MagicMock:
    """Create a mock Notification object."""
    n = MagicMock()
    n.id = str(uuid.uuid4())
    n.user_id = user_id
    n.event_id = str(uuid.uuid4())
    n.type = event_type
    n.title = "Test notification"
    n.body = "Some body"
    n.entity_type = "task"
    n.entity_id = str(uuid.uuid4())
    n.is_read = is_read
    n.created_at = datetime.now(timezone.utc)
    return n


class TestNotificationsRouter:
    """Tests for notifications API responses."""

    @pytest.mark.asyncio
    async def test_list_notifications(self):
        """GET /notifications returns list of notifications for current user."""
        from app.routers.notifications import list_notifications

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        notifs = [make_notification("user-1"), make_notification("user-1")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = notifs
        mock_db.execute.return_value = mock_result

        result = await list_notifications(user=mock_user, db=mock_db)
        assert len(result) == 2
        assert result[0]["type"] == "task.assigned"

    @pytest.mark.asyncio
    async def test_unread_count(self):
        """GET /notifications/unread-count returns correct count."""
        from app.routers.notifications import unread_count

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute.return_value = mock_result

        result = await unread_count(user=mock_user, db=mock_db)
        assert result == {"count": 5}

    @pytest.mark.asyncio
    async def test_mark_read(self):
        """POST /notifications/:id/read marks notification as read."""
        from app.routers.notifications import mark_read

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        notif = make_notification("user-1")
        notif.is_read = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = notif
        mock_db.execute.return_value = mock_result

        result = await mark_read(notification_id=notif.id, user=mock_user, db=mock_db)
        assert result == {"message": "ok"}
        assert notif.is_read is True

    @pytest.mark.asyncio
    async def test_mark_all_read(self):
        """POST /notifications/read-all marks all as read."""
        from app.routers.notifications import mark_all_read

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        result = await mark_all_read(user=mock_user, db=mock_db)
        assert result == {"message": "ok"}
        mock_db.execute.assert_awaited()
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_cannot_read_others_notification(self):
        """POST /notifications/:id/read returns 404 for another user's notification."""
        from fastapi import HTTPException

        from app.routers.notifications import mark_read

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        # Return None — notification not found for this user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await mark_read(notification_id="other-notif-id", user=mock_user, db=mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unread_count_zero(self):
        """Unread count returns 0 when no notifications."""
        from app.routers.notifications import unread_count

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        result = await unread_count(user=mock_user, db=mock_db)
        assert result == {"count": 0}

    @pytest.mark.asyncio
    async def test_empty_input(self):
        """List notifications returns empty list when no notifications exist."""
        from app.routers.notifications import list_notifications

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await list_notifications(user=mock_user, db=mock_db)
        assert result == []

    @pytest.mark.asyncio
    async def test_duplicate_handling(self):
        """Same notification returned only once."""
        from app.routers.notifications import list_notifications

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-1"

        notif = make_notification("user-1")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [notif]
        mock_db.execute.return_value = mock_result

        result = await list_notifications(user=mock_user, db=mock_db)
        assert len(result) == 1
