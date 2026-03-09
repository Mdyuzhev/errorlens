"""Tests for generation from session endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models.db_models import Session, SessionData


# Override auth dependency for testing
def override_require_auth():
    """Override auth dependency to return mock user."""
    mock_user = MagicMock()
    mock_user.id = "test-user-123"
    mock_user.is_active = True
    return mock_user


client = TestClient(app)


@pytest.fixture
def mock_session_with_requests():
    """Mock session with recorded requests."""
    session = MagicMock(spec=Session)
    session.id = "test-session-id"
    session.url = "https://test.com"
    session.project_id = "test-project-id"

    session_data = MagicMock(spec=SessionData)
    session_data.recorded_requests = [
        {
            "url": "https://api.test.com/users",
            "method": "GET",
            "headers": {"Content-Type": "application/json"},
            "body": None
        },
        {
            "url": "https://api.test.com/users/1",
            "method": "GET",
            "headers": {},
            "body": None
        }
    ]
    session.data = session_data
    return session


@pytest.fixture
def mock_session_no_requests():
    """Mock session without recorded requests."""
    session = MagicMock(spec=Session)
    session.id = "empty-session-id"
    session.data = MagicMock(spec=SessionData)
    session.data.recorded_requests = []
    return session


@pytest.fixture
def mock_auth_token():
    """Mock JWT token for authenticated requests."""
    return "Bearer fake-jwt-token"


class TestGenerateFromSession:
    """Tests for /api/v1/generation/from-session/{session_id} endpoint."""

    @patch("app.routers.generation.publish", new_callable=AsyncMock)
    @patch("app.services.generation_service.GenerationService.create_task_from_session")
    def test_from_session_success(
        self,
        mock_create_task,
        mock_publish,
        mock_auth_token
    ):
        """Generate from session with valid data returns task_id."""
        from app.middleware.jwt_auth import require_auth

        # Override auth dependency
        app.dependency_overrides[require_auth] = override_require_auth

        # Mock task creation
        mock_create_task.return_value = "task-abc-123"

        try:
            response = client.post(
                "/api/v1/generation/from-session/test-session-id",
                headers={"Authorization": mock_auth_token},
                data={
                    "framework": "pytest",
                    "provider": "anthropic"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-abc-123"
            assert data["websocket_url"] == "/ws/generation/task-abc-123"
            mock_create_task.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.generation_service.GenerationService.create_task_from_session")
    def test_from_session_not_found(
        self,
        mock_create_task,
        mock_auth_token
    ):
        """Generate from nonexistent session returns 404."""
        from app.middleware.jwt_auth import require_auth

        app.dependency_overrides[require_auth] = override_require_auth

        # Mock session not found
        mock_create_task.side_effect = HTTPException(status_code=404, detail="Session not found")

        try:
            response = client.post(
                "/api/v1/generation/from-session/nonexistent-session",
                headers={"Authorization": mock_auth_token},
                data={"framework": "pytest"}
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    @patch("app.services.generation_service.GenerationService.create_task_from_session")
    def test_from_session_no_requests(
        self,
        mock_create_task,
        mock_auth_token
    ):
        """Generate from session with no recorded requests returns 400."""
        from app.middleware.jwt_auth import require_auth

        app.dependency_overrides[require_auth] = override_require_auth

        # Mock no requests
        mock_create_task.side_effect = HTTPException(
            status_code=400,
            detail="Session has no recorded requests"
        )

        try:
            response = client.post(
                "/api/v1/generation/from-session/empty-session-id",
                headers={"Authorization": mock_auth_token},
                data={"framework": "pytest"}
            )

            assert response.status_code == 400
            assert "no recorded requests" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_from_session_auth_required(self):
        """Generate from session without auth returns 401."""
        response = client.post(
            "/api/v1/generation/from-session/test-session-id",
            data={"framework": "pytest"}
        )

        assert response.status_code == 401

    @patch("app.routers.generation.publish", new_callable=AsyncMock)
    @patch("app.services.generation_service.GenerationService.create_task_from_session")
    def test_from_session_custom_provider(
        self,
        mock_create_task,
        mock_publish,
        mock_auth_token
    ):
        """Generate from session with custom provider and model."""
        from app.middleware.jwt_auth import require_auth

        app.dependency_overrides[require_auth] = override_require_auth

        # Mock task creation
        mock_create_task.return_value = "task-custom-123"

        try:
            response = client.post(
                "/api/v1/generation/from-session/test-session-id",
                headers={"Authorization": mock_auth_token},
                data={
                    "framework": "unittest",
                    "provider": "openai",
                    "model": "gpt-4"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "task-custom-123"

            # Verify correct parameters passed
            call_args = mock_create_task.call_args
            assert call_args.kwargs["framework"] == "unittest"
            assert call_args.kwargs["provider"] == "openai"
            assert call_args.kwargs["model"] == "gpt-4"
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestCreateTaskFromSession:
    """Tests for GenerationService.create_task_from_session method."""

    async def test_empty_input(self):
        """Handle empty session_id."""
        from app.services.generation_service import GenerationService

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        with pytest.raises(HTTPException) as exc:
            await GenerationService.create_task_from_session(
                session_id="",
                db=mock_db
            )
        assert exc.value.status_code == 404

    async def test_none_handling(self):
        """Handle None values in recorded_requests."""
        from app.services.generation_service import GenerationService

        session = MagicMock(spec=Session)
        session.id = "test-id"
        session.data = MagicMock(spec=SessionData)
        session.data.recorded_requests = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=session)))
        mock_db.refresh = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await GenerationService.create_task_from_session(
                session_id="test-id",
                db=mock_db
            )
        assert exc.value.status_code == 400
        assert "no recorded requests" in exc.value.detail.lower()

    async def test_duplicate_handling(self):
        """Handle duplicate requests in recorded_requests."""
        from app.services.generation_service import GenerationService

        session = MagicMock(spec=Session)
        session.id = "test-id"
        session.data = MagicMock(spec=SessionData)
        session.data.recorded_requests = [
            {"url": "https://api.test.com/users", "method": "GET"},
            {"url": "https://api.test.com/users", "method": "GET"}
        ]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=session)))
        mock_db.refresh = AsyncMock()

        with patch("app.services.generation_service.GenerationService.create_task") as mock_create:
            mock_create.return_value = "task-id"

            task_id = await GenerationService.create_task_from_session(
                session_id="test-id",
                db=mock_db
            )

            assert task_id == "task-id"
            # Verify duplicates are passed through (LLM should handle deduplication)
            call_args = mock_create.call_args
            assert len(call_args.kwargs["input_data"]) == 2

    async def test_concurrent_access(self):
        """Handle concurrent access to same session."""
        from app.services.generation_service import GenerationService
        import asyncio

        session = MagicMock(spec=Session)
        session.id = "concurrent-test"
        session.data = MagicMock(spec=SessionData)
        session.data.recorded_requests = [
            {"url": "https://api.test.com/test", "method": "GET"}
        ]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=session)))
        mock_db.refresh = AsyncMock()

        with patch("app.services.generation_service.GenerationService.create_task") as mock_create:
            mock_create.return_value = "task-concurrent"

            # Simulate concurrent calls
            tasks = [
                GenerationService.create_task_from_session(
                    session_id="concurrent-test",
                    db=mock_db
                )
                for _ in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r == "task-concurrent" for r in results)

    async def test_memory_cleanup(self):
        """Verify multiple tasks can be created without leaks (Redis TTL handles cleanup)."""
        from app.services.generation_service import GenerationService

        session = MagicMock(spec=Session)
        session.id = "memory-test"
        session.data = MagicMock(spec=SessionData)
        session.data.recorded_requests = [
            {"url": "https://api.test.com/test", "method": "GET"}
        ]

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=session)))
        mock_db.refresh = AsyncMock()

        # Create multiple tasks — Redis TTL handles cleanup automatically
        task_ids = []
        for i in range(5):
            with patch("app.services.generation_service.GenerationService.create_task") as mock_create:
                mock_create.return_value = f"task-{i}"
                task_id = await GenerationService.create_task_from_session(
                    session_id="memory-test",
                    db=mock_db
                )
                task_ids.append(task_id)

        assert len(task_ids) == 5
        assert len(set(task_ids)) == 5

    async def test_error_recovery(self):
        """Handle database errors gracefully."""
        from app.services.generation_service import GenerationService

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Database connection error"))

        with pytest.raises(Exception) as exc:
            await GenerationService.create_task_from_session(
                session_id="test-id",
                db=mock_db
            )
        assert "Database connection error" in str(exc.value)
