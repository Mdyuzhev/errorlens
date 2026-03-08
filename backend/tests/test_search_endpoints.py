"""Tests for search (q param) in list endpoints for testcases, tasks, articles."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.testcase_service import TestCaseService
from app.services.task_service import TaskService
from app.services.article_service import ArticleService


def _mock_testcase(id_: str, title: str, description: str = ""):
    tc = MagicMock()
    tc.id = id_
    tc.title = title
    tc.description = description
    tc.preconditions = None
    tc.postconditions = None
    tc.priority = "Medium"
    tc.status = "Draft"
    tc.automation_status = "Manual"
    tc.folder = None
    tc.folder_id = None
    tc.tags = []
    tc.steps = []
    tc.created_at = None
    tc.created_by = "tester"
    tc.session_id = None
    tc.external_id = None
    tc.external_url = None
    tc.updated_at = None
    return tc


def _mock_task(id_: str, title: str, description: str = ""):
    t = MagicMock()
    t.id = id_
    t.title = title
    t.description = description
    t.status = "todo"
    t.priority = "medium"
    t.assignee = None
    t.labels = []
    t.due_date = None
    t.created_at = None
    t.completed_at = None
    t.session_id = None
    t.testcase_id = None
    return t


def _mock_article(id_: str, title: str, content: str = ""):
    a = MagicMock()
    a.id = id_
    a.title = title
    a.slug = title.lower().replace(" ", "-")
    a.content = content
    a.excerpt = content[:200]
    a.category = None
    a.tags = []
    a.status = "draft"
    a.author = "tester"
    a.project_id = None
    a.folder_id = None
    a.created_at = None
    a.views = 0
    a.published_at = None
    return a


class TestTestCaseSearchParam:
    """Tests for testcases list with q param."""

    @pytest.fixture
    def service(self):
        db = AsyncMock()
        svc = TestCaseService(db)
        svc.repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_search_testcases_returns_results(self, service):
        """search_testcases returns matching items."""
        tc = _mock_testcase("tc1", "Login test")
        service.repo.search = AsyncMock(return_value=[tc])

        result = await service.search_testcases("Login", limit=10, offset=0)

        assert len(result) == 1
        assert result[0]["title"] == "Login test"
        service.repo.search.assert_called_once_with("Login", skip=0, limit=10)

    @pytest.mark.asyncio
    async def test_search_testcases_empty_result(self, service):
        """search_testcases returns empty list when nothing matches."""
        service.repo.search = AsyncMock(return_value=[])

        result = await service.search_testcases("nonexistent", limit=10, offset=0)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_without_q_works(self, service):
        """list_testcases works normally without q."""
        tc = _mock_testcase("tc1", "Test case 1")
        service.repo.get_all = AsyncMock(return_value=[tc])

        result = await service.list_testcases(limit=50, offset=0)

        assert len(result) == 1
        assert result[0]["id"] == "tc1"


class TestTaskSearchParam:
    """Tests for tasks list with q param."""

    @pytest.fixture
    def service(self):
        db = AsyncMock()
        svc = TaskService(db)
        svc.repo = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_search_tasks_returns_results(self, service):
        """search_tasks returns matching items."""
        task = _mock_task("t1", "Fix login bug")
        service.repo.search = AsyncMock(return_value=[task])

        result = await service.search_tasks("login", limit=20)

        assert len(result) == 1
        assert result[0]["title"] == "Fix login bug"
        service.repo.search.assert_called_once_with("login", limit=20)

    @pytest.mark.asyncio
    async def test_search_tasks_empty_result(self, service):
        """search_tasks returns empty list when nothing matches."""
        service.repo.search = AsyncMock(return_value=[])

        result = await service.search_tasks("nonexistent", limit=20)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_without_q_works(self, service):
        """list_tasks works normally without q."""
        task = _mock_task("t1", "Task 1")
        service.repo.list_with_filters = AsyncMock(return_value=[task])

        result = await service.list_tasks()

        assert len(result) == 1
        assert result[0]["id"] == "t1"


class TestArticleSearchParam:
    """Tests for articles list with q param."""

    @pytest.fixture
    def service(self):
        db = AsyncMock()
        svc = ArticleService(db)
        svc.repo = AsyncMock()
        svc.entity_link_service = AsyncMock()
        return svc

    @pytest.mark.asyncio
    async def test_search_articles_returns_results(self, service):
        """search_articles returns matching items."""
        article = _mock_article("a1", "API Guide", "How to use our API")
        service.repo.search = AsyncMock(return_value=[article])

        result = await service.search_articles("API", project_id=None, limit=10)

        assert len(result) == 1
        assert result[0]["title"] == "API Guide"
        service.repo.search.assert_called_once_with("API", project_id=None, limit=10)

    @pytest.mark.asyncio
    async def test_search_articles_with_project_id(self, service):
        """search_articles filters by project_id."""
        article = _mock_article("a1", "Scoped article")
        service.repo.search = AsyncMock(return_value=[article])

        result = await service.search_articles("Scoped", project_id="proj-1", limit=10)

        service.repo.search.assert_called_once_with("Scoped", project_id="proj-1", limit=10)

    @pytest.mark.asyncio
    async def test_search_articles_empty_result(self, service):
        """search_articles returns empty list when nothing matches."""
        service.repo.search = AsyncMock(return_value=[])

        result = await service.search_articles("nonexistent", project_id=None, limit=10)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_without_q_works(self, service):
        """list_articles works normally without q."""
        article = _mock_article("a1", "Article 1")
        service.repo.list_with_filters = AsyncMock(return_value=[article])

        result = await service.list_articles()

        assert len(result) == 1
        assert result[0]["id"] == "a1"
