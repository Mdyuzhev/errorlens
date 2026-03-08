"""Tests for admin CRUD bypass and seed demo data."""

import os

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://errorlens:errorlens_secret@localhost:5432/errorlens"
    )

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.middleware.jwt_auth import check_project_access, get_default_project
from app.models.db_models import Article, ArticleFolder, TestCase, TestCaseFolder, Project
from app.models.user import User


def _make_user(is_admin: bool = False, user_id: str = "user-1") -> User:
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.is_admin = is_admin
    user.is_active = True
    return user


def _make_project(owner_id: str = "owner-1", project_id: str = "proj-1") -> Project:
    """Create a mock project."""
    project = MagicMock(spec=Project)
    project.id = project_id
    project.owner_id = owner_id
    return project


class TestAdminCheckProjectAccess:
    """Tests for admin bypass in check_project_access."""

    @pytest.mark.asyncio
    async def test_admin_can_access_any_project(self):
        """Admin should bypass all membership checks."""
        admin = _make_user(is_admin=True, user_id="admin-1")
        project = _make_project(owner_id="other-user", project_id="proj-1")

        db = AsyncMock()
        # Mock: project found
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = project
        db.execute.return_value = result_mock

        result = await check_project_access("proj-1", admin, db)
        assert result == project

    @pytest.mark.asyncio
    async def test_admin_project_not_found_returns_404(self):
        """Admin should get 404 if project doesn't exist."""
        from fastapi import HTTPException

        admin = _make_user(is_admin=True, user_id="admin-1")

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await check_project_access("nonexistent", admin, db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_non_admin_without_membership_gets_403(self):
        """Non-admin without membership should get 403."""
        from fastapi import HTTPException

        user = _make_user(is_admin=False, user_id="user-1")
        project = _make_project(owner_id="other-user", project_id="proj-1")

        db = AsyncMock()
        # First call: find project
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        # Second call: find membership — not found
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [project_result, member_result]

        with pytest.raises(HTTPException) as exc_info:
            await check_project_access("proj-1", user, db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_can_access_own_project(self):
        """Owner should access their own project."""
        user = _make_user(is_admin=False, user_id="owner-1")
        project = _make_project(owner_id="owner-1", project_id="proj-1")

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = project
        db.execute.return_value = result_mock

        result = await check_project_access("proj-1", user, db)
        assert result == project


class TestAdminGetDefaultProject:
    """Tests for admin fallback in get_default_project."""

    @pytest.mark.asyncio
    async def test_admin_fallback_to_any_project(self):
        """Admin without own projects should get first project in system."""
        admin = _make_user(is_admin=True, user_id="admin-1")
        any_project = _make_project(owner_id="other-user", project_id="fallback-proj")

        db = AsyncMock()
        # owned — None
        owned_result = MagicMock()
        owned_result.scalar_one_or_none.return_value = None
        # member — None
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = None
        # any project — found
        any_result = MagicMock()
        any_result.scalar_one_or_none.return_value = any_project

        db.execute.side_effect = [owned_result, member_result, any_result]

        result = await get_default_project(admin, db)
        assert result == any_project

    @pytest.mark.asyncio
    async def test_admin_with_owned_project(self):
        """Admin with owned project should get it directly."""
        admin = _make_user(is_admin=True, user_id="admin-1")
        owned = _make_project(owner_id="admin-1", project_id="admin-proj")

        db = AsyncMock()
        owned_result = MagicMock()
        owned_result.scalar_one_or_none.return_value = owned
        db.execute.return_value = owned_result

        result = await get_default_project(admin, db)
        assert result == owned

    @pytest.mark.asyncio
    async def test_non_admin_no_projects_returns_none(self):
        """Non-admin without any projects should get None."""
        user = _make_user(is_admin=False, user_id="user-1")

        db = AsyncMock()
        owned_result = MagicMock()
        owned_result.scalar_one_or_none.return_value = None
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = None
        db.execute.side_effect = [owned_result, member_result]

        result = await get_default_project(user, db)
        assert result is None


class TestSeedDemoConstants:
    """Tests for seed demo data constants."""

    def test_demo_articles_count(self):
        """Should have at least 15 demo articles."""
        from app.services.seed_demo_articles import DEMO_ARTICLES

        assert len(DEMO_ARTICLES) >= 15

    def test_demo_articles_have_required_fields(self):
        """Every article should have all required fields."""
        from app.services.seed_demo_articles import DEMO_ARTICLES

        required = {
            "title",
            "slug",
            "content",
            "excerpt",
            "category",
            "tags",
            "status",
            "author",
            "folder_key",
        }
        for art in DEMO_ARTICLES:
            missing = required - set(art.keys())
            assert not missing, f"Article '{art['title']}' missing fields: {missing}"

    def test_demo_articles_have_project_folder_keys(self):
        """All folder_keys should map to existing folders."""
        from app.services.seed_demo_articles import DEMO_ARTICLES, DEMO_ARTICLE_FOLDER_MAP

        for art in DEMO_ARTICLES:
            assert (
                art["folder_key"] in DEMO_ARTICLE_FOLDER_MAP
            ), f"Article '{art['title']}' has unknown folder_key: {art['folder_key']}"

    def test_demo_articles_unique_slugs(self):
        """All article slugs should be unique."""
        from app.services.seed_demo_articles import DEMO_ARTICLES

        slugs = [a["slug"] for a in DEMO_ARTICLES]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_demo_article_folders_at_least_8(self):
        """Should have at least 8 unique article folders (including subfolders)."""
        from app.services.seed_demo_articles import DEMO_ARTICLE_FOLDERS

        total = sum(1 + len(subs) for subs in DEMO_ARTICLE_FOLDERS.values())
        assert total >= 8

    def test_demo_testcases_count(self):
        """Should have at least 20 demo test cases."""
        from app.services.seed_demo_constants import DEMO_TEST_CASES

        assert len(DEMO_TEST_CASES) >= 20

    def test_demo_testcases_have_required_fields(self):
        """Every test case should have all required fields."""
        from app.services.seed_demo_constants import DEMO_TEST_CASES

        required = {
            "title",
            "description",
            "preconditions",
            "postconditions",
            "priority",
            "status",
            "folder",
            "tags",
            "steps",
        }
        for tc in DEMO_TEST_CASES:
            missing = required - set(tc.keys())
            assert not missing, f"TestCase '{tc['title']}' missing fields: {missing}"

    def test_demo_testcase_folders_expanded(self):
        """Testcase folders should have expanded structure."""
        from app.services.seed_demo_constants import DEMO_TESTCASE_FOLDERS

        # Per task: JWT subfolder in Авторизация, Auth in API, etc.
        assert "JWT" in DEMO_TESTCASE_FOLDERS.get("Авторизация", [])
        assert "Auth" in DEMO_TESTCASE_FOLDERS.get("API", [])
        assert "Cypress" in DEMO_TESTCASE_FOLDERS.get("Экспорт", [])
        assert "AuthBypass" in DEMO_TESTCASE_FOLDERS.get("Security", [])

    def test_welcome_article_has_all_fields(self):
        """Welcome article should have all required fields."""
        from app.services.seed_demo_articles import WELCOME_ARTICLE

        required = {"title", "slug", "content", "excerpt", "category", "tags", "status", "author"}
        missing = required - set(WELCOME_ARTICLE.keys())
        assert not missing, f"Welcome article missing: {missing}"

    def test_demo_articles_content_min_length(self):
        """Each article content should be at least 200 chars."""
        from app.services.seed_demo_articles import DEMO_ARTICLES

        for art in DEMO_ARTICLES:
            assert (
                len(art["content"]) >= 200
            ), f"Article '{art['title']}' content too short: {len(art['content'])} chars"


# ─── Edge cases & concurrency ───────────────────────────────────────


class TestAdminEdgeCases:
    """Edge cases for admin access checks."""

    @pytest.mark.asyncio
    async def test_empty_project_id_returns_404(self):
        """Empty string project_id returns 404."""
        from fastapi import HTTPException

        admin = _make_user(is_admin=True)
        db = AsyncMock()
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        db.execute.return_value = r

        with pytest.raises(HTTPException) as exc:
            await check_project_access("", admin, db)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_duplicate_access_checks(self):
        """Calling check_project_access twice works correctly."""
        admin = _make_user(is_admin=True)
        project = _make_project(owner_id="x", project_id="p1")

        r1 = MagicMock()
        r1.scalar_one_or_none.return_value = project
        r2 = MagicMock()
        r2.scalar_one_or_none.return_value = project

        db = AsyncMock()
        db.execute.side_effect = [r1, r2]

        res1 = await check_project_access("p1", admin, db)
        res2 = await check_project_access("p1", admin, db)
        assert res1.id == res2.id

    @pytest.mark.asyncio
    async def test_concurrent_admin_access(self):
        """Multiple concurrent admin access checks don't interfere."""
        import asyncio

        admin = _make_user(is_admin=True)

        async def check_one(pid: str):
            project = _make_project(project_id=pid, owner_id="x")
            db = AsyncMock()
            r = MagicMock()
            r.scalar_one_or_none.return_value = project
            db.execute.return_value = r
            return await check_project_access(pid, admin, db)

        results = await asyncio.gather(check_one("p1"), check_one("p2"), check_one("p3"))
        assert [r.id for r in results] == ["p1", "p2", "p3"]

    @pytest.mark.asyncio
    async def test_error_recovery_after_404(self):
        """After 404, next check works fine."""
        from fastapi import HTTPException

        admin = _make_user(is_admin=True)

        db_none = AsyncMock()
        r_none = MagicMock()
        r_none.scalar_one_or_none.return_value = None
        db_none.execute.return_value = r_none

        with pytest.raises(HTTPException):
            await check_project_access("gone", admin, db_none)

        project = _make_project(project_id="p2", owner_id="x")
        db_ok = AsyncMock()
        r_ok = MagicMock()
        r_ok.scalar_one_or_none.return_value = project
        db_ok.execute.return_value = r_ok

        result = await check_project_access("p2", admin, db_ok)
        assert result.id == "p2"

    @pytest.mark.asyncio
    async def test_member_role_hierarchy(self):
        """Member role can access member-level but not admin-level."""
        from fastapi import HTTPException

        user = _make_user(is_admin=False, user_id="u1")
        project = _make_project(owner_id="other", project_id="p1")
        member = MagicMock()
        member.user_id = "u1"
        member.role = "member"

        def make_db():
            db = AsyncMock()
            r1 = MagicMock()
            r1.scalar_one_or_none.return_value = project
            r2 = MagicMock()
            r2.scalar_one_or_none.return_value = member
            db.execute.side_effect = [r1, r2]
            return db

        # member role sufficient for "member"
        result = await check_project_access("p1", user, make_db(), required_role="member")
        assert result.id == "p1"

        # member role insufficient for "admin"
        with pytest.raises(HTTPException) as exc:
            await check_project_access("p1", user, make_db(), required_role="admin")
        assert exc.value.status_code == 403
