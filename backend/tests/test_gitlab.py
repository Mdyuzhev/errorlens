"""Tests for GitLab integration: crypto, service, router."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ============= Crypto Utils =============


class TestCrypto:
    """Tests for encrypt/decrypt/mask utilities."""

    def test_encrypt_decrypt(self):
        """encrypt → decrypt returns original."""
        from app.utils.crypto import decrypt_token, encrypt_token

        original = "glpat-abc123-secret-token"
        encrypted = encrypt_token(original)
        assert encrypted != original
        decrypted = decrypt_token(encrypted)
        assert decrypted == original

    def test_encrypt_different_each_time(self):
        """Each encryption produces different ciphertext (Fernet uses nonce)."""
        from app.utils.crypto import encrypt_token

        a = encrypt_token("same-token")
        b = encrypt_token("same-token")
        assert a != b

    def test_mask_token(self):
        """mask_token shows first 4 chars + ****."""
        from app.utils.crypto import mask_token

        assert mask_token("glpat-abc123") == "glpa****"

    def test_mask_token_short(self):
        """Short tokens are fully masked."""
        from app.utils.crypto import mask_token

        assert mask_token("ab") == "****"

    def test_token_not_in_response(self):
        """ConnectionResponse schema does not expose plain token."""
        from app.schemas.gitlab import ConnectionResponse

        fields = ConnectionResponse.model_fields
        assert "token" not in fields
        assert "token_encrypted" not in fields
        assert "token_masked" in fields


# ============= GitLab Service =============


def _make_connection(url: str = "http://gitlab.test", verify_ssl: bool = True) -> MagicMock:
    """Create a mock GitLabConnection."""
    from app.utils.crypto import encrypt_token

    conn = MagicMock()
    conn.url = url
    conn.verify_ssl = verify_ssl
    conn.token_encrypted = encrypt_token("glpat-test-token")
    return conn


class TestGitLabService:
    """Tests for GitLabService with mocked httpx."""

    @pytest.mark.asyncio
    async def test_check_connection_ok(self):
        """Mocked 200 → {ok: True, username}."""
        from app.services.gitlab_service import GitLabService

        svc = GitLabService()
        conn = _make_connection()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"username": "john_doe", "id": 1}
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.gitlab_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await svc.check_connection(conn)
            assert result["ok"] is True
            assert result["username"] == "john_doe"

    @pytest.mark.asyncio
    async def test_check_connection_fail(self):
        """ConnectError → {ok: False, error}."""
        from app.services.gitlab_service import GitLabService

        svc = GitLabService()
        conn = _make_connection()

        with patch("app.services.gitlab_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.side_effect = httpx.ConnectError("refused")
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await svc.check_connection(conn)
            assert result["ok"] is False
            assert "refused" in result["error"]

    @pytest.mark.asyncio
    async def test_check_connection_401(self):
        """401 → {ok: False, error about token}."""
        from app.services.gitlab_service import GitLabService

        svc = GitLabService()
        conn = _make_connection()

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("app.services.gitlab_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            result = await svc.check_connection(conn)
            assert result["ok"] is False
            assert "token" in result["error"].lower() or "expired" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_projects(self):
        """Mocked projects list returns mapped fields."""
        from app.services.gitlab_service import GitLabService

        svc = GitLabService()
        conn = _make_connection()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 42,
                "name": "My Project",
                "path_with_namespace": "group/my-project",
                "web_url": "http://gitlab.test/group/my-project",
                "default_branch": "main",
            }
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.gitlab_service.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.request.return_value = mock_response
            client_instance.__aenter__ = AsyncMock(return_value=client_instance)
            client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = client_instance

            projects = await svc.get_projects(conn)
            assert len(projects) == 1
            assert projects[0]["id"] == 42
            assert projects[0]["name"] == "My Project"

    @pytest.mark.asyncio
    async def test_delete_connection(self):
        """Repository delete removes the record."""
        # This is a unit test for the delete flow
        from app.repositories.gitlab_connection_repo import GitLabConnectionRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result
        mock_session.flush = AsyncMock()

        repo = GitLabConnectionRepository(mock_session)
        deleted = await repo.delete("some-uuid")
        assert deleted is True

    def test_empty_input(self):
        """CreateConnectionRequest requires non-empty fields."""
        from pydantic import ValidationError

        from app.schemas.gitlab import CreateConnectionRequest

        with pytest.raises(ValidationError):
            CreateConnectionRequest(name="", url="", token="")

    def test_none_handling(self):
        """UpdateConnectionRequest allows all None."""
        from app.schemas.gitlab import UpdateConnectionRequest

        req = UpdateConnectionRequest()
        assert req.name is None
        assert req.token is None

    def test_duplicate_handling(self):
        """Two connections with same name are allowed (no unique constraint)."""
        from app.schemas.gitlab import CreateConnectionRequest

        a = CreateConnectionRequest(name="Same", url="http://a", token="t1")
        b = CreateConnectionRequest(name="Same", url="http://b", token="t2")
        assert a.name == b.name
