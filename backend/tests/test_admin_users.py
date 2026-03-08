"""Tests for admin users endpoints."""

import os

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://errorlens:errorlens_secret@localhost:5432/errorlens"
    )

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.routers.admin import (
    AdminPasswordChange,
    AdminToggleActive,
    AdminUserCreate,
    AdminUserResponse,
    require_admin,
)
from app.models.user import User


def _mock_user(
    user_id: str = "u1",
    username: str = "testuser",
    is_admin: bool = False,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.username = username
    user.is_admin = is_admin
    user.is_active = is_active
    user.created_at = None
    user.last_login = None
    user.hashed_password = "hashed"
    return user


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    def test_admin_passes(self) -> None:
        admin = _mock_user(is_admin=True)
        result = require_admin(admin)
        assert result == admin

    def test_non_admin_raises_403(self) -> None:
        user = _mock_user(is_admin=False)
        with pytest.raises(HTTPException) as exc:
            require_admin(user)
        assert exc.value.status_code == 403


class TestListUsers:
    """Tests for GET /admin/users."""

    @pytest.mark.asyncio
    async def test_list_users_as_admin(self) -> None:
        from app.routers.admin import list_users

        u1 = _mock_user(user_id="u1", username="alice", is_admin=True)
        u2 = _mock_user(user_id="u2", username="bob", is_admin=False)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [u1, u2]
        db.execute.return_value = result_mock

        admin = _mock_user(is_admin=True)
        result = await list_users(db=db, user=admin)
        assert len(result) == 2
        assert result[0].username == "alice"
        assert result[1].username == "bob"

    @pytest.mark.asyncio
    async def test_list_users_as_non_admin(self) -> None:
        """Non-admin should be blocked by require_admin."""
        user = _mock_user(is_admin=False)
        with pytest.raises(HTTPException) as exc:
            require_admin(user)
        assert exc.value.status_code == 403


class TestCreateUser:
    """Tests for POST /admin/users."""

    @pytest.mark.asyncio
    async def test_create_user(self) -> None:
        from app.routers.admin import create_user_endpoint

        db = AsyncMock()
        # No existing user
        existing_mock = MagicMock()
        existing_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = existing_mock

        new_user = _mock_user(user_id="new-1", username="newuser", is_admin=False)

        with patch("app.routers.admin.create_user", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = new_user
            data = AdminUserCreate(username="newuser", password="pass123", is_admin=False)
            admin = _mock_user(is_admin=True)
            result = await create_user_endpoint(data=data, db=db, user=admin)
            assert result.username == "newuser"
            mock_create.assert_called_once_with(db, "newuser", "pass123", False)

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self) -> None:
        from app.routers.admin import create_user_endpoint

        db = AsyncMock()
        existing_mock = MagicMock()
        existing_mock.scalar_one_or_none.return_value = _mock_user(username="dup")
        db.execute.return_value = existing_mock

        data = AdminUserCreate(username="dup", password="pass123")
        admin = _mock_user(is_admin=True)

        with pytest.raises(HTTPException) as exc:
            await create_user_endpoint(data=data, db=db, user=admin)
        assert exc.value.status_code == 400


class TestChangePassword:
    """Tests for PATCH /admin/users/{user_id}/password."""

    @pytest.mark.asyncio
    async def test_change_password(self) -> None:
        from app.routers.admin import change_user_password

        target = _mock_user(user_id="t1", username="target")

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = target
        db.execute.return_value = result_mock

        with patch("app.routers.admin.get_password_hash", return_value="newhash"):
            data = AdminPasswordChange(new_password="newpass123")
            admin = _mock_user(is_admin=True)
            result = await change_user_password(
                user_id="t1", data=data, db=db, admin=admin
            )
            assert result["message"] == "Password changed"
            assert target.hashed_password == "newhash"
            db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self) -> None:
        from app.routers.admin import change_user_password

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        data = AdminPasswordChange(new_password="newpass123")
        admin = _mock_user(is_admin=True)

        with pytest.raises(HTTPException) as exc:
            await change_user_password(
                user_id="nonexistent", data=data, db=db, admin=admin
            )
        assert exc.value.status_code == 404


class TestToggleActive:
    """Tests for PATCH /admin/users/{user_id}/active."""

    @pytest.mark.asyncio
    async def test_toggle_active(self) -> None:
        from app.routers.admin import toggle_user_active

        target = _mock_user(user_id="t1", username="target", is_active=True)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = target
        db.execute.return_value = result_mock

        data = AdminToggleActive(is_active=False)
        admin = _mock_user(is_admin=True)
        result = await toggle_user_active(
            user_id="t1", data=data, db=db, admin=admin
        )
        assert result.is_active is False
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_toggle_active_user_not_found(self) -> None:
        from app.routers.admin import toggle_user_active

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        data = AdminToggleActive(is_active=False)
        admin = _mock_user(is_admin=True)

        with pytest.raises(HTTPException) as exc:
            await toggle_user_active(
                user_id="nonexistent", data=data, db=db, admin=admin
            )
        assert exc.value.status_code == 404


class TestInactiveUserCannotLogin:
    """Test that inactive user cannot authenticate."""

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_login(self) -> None:
        from app.services.auth import authenticate_user

        inactive_user = _mock_user(is_active=False)
        inactive_user.hashed_password = "$2b$12$fakehash"

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = inactive_user
        db.execute.return_value = result_mock

        with patch("app.services.auth.verify_password", return_value=True):
            result = await authenticate_user(db, "testuser", "password")
            assert result is None


class TestEdgeCases:
    """Edge cases and validation."""

    def test_username_min_length_validation(self) -> None:
        with pytest.raises(Exception):
            AdminUserCreate(username="ab", password="pass123")

    def test_password_min_length_validation(self) -> None:
        with pytest.raises(Exception):
            AdminUserCreate(username="valid", password="short")

    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self) -> None:
        """Multiple concurrent creates don't interfere."""
        import asyncio
        from app.routers.admin import create_user_endpoint

        async def create_one(username: str) -> AdminUserResponse:
            db = AsyncMock()
            existing_mock = MagicMock()
            existing_mock.scalar_one_or_none.return_value = None
            db.execute.return_value = existing_mock

            new_user = _mock_user(user_id=f"id-{username}", username=username)
            with patch("app.routers.admin.create_user", new_callable=AsyncMock) as m:
                m.return_value = new_user
                data = AdminUserCreate(username=username, password="pass123")
                admin = _mock_user(is_admin=True)
                return await create_user_endpoint(data=data, db=db, user=admin)

        results = await asyncio.gather(
            create_one("user_a"), create_one("user_b"), create_one("user_c")
        )
        assert [r.username for r in results] == ["user_a", "user_b", "user_c"]

    def test_admin_user_response_from_attributes(self) -> None:
        user = _mock_user(user_id="x", username="foo", is_admin=True, is_active=True)
        resp = AdminUserResponse.model_validate(user)
        assert resp.id == "x"
        assert resp.username == "foo"
        assert resp.is_admin is True
