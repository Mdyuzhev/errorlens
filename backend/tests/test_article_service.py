"""Tests for ArticleService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.article_service import ArticleService, slugify


class TestSlugify:
    """Tests for slugify helper function."""

    def test_slugify_basic(self):
        """Test basic slugification."""
        assert slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        """Test slugify removes special characters."""
        assert slugify("Hello! @World#") == "hello-world"

    def test_slugify_multiple_spaces(self):
        """Test slugify handles multiple spaces."""
        assert slugify("Hello   World") == "hello-world"

    def test_slugify_max_length(self):
        """Test slugify truncates to 200 chars."""
        long_title = "a" * 300
        assert len(slugify(long_title)) == 200


class TestArticleService:
    """Tests for ArticleService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def mock_repo(self):
        """Create mock ArticleRepository."""
        repo = AsyncMock()
        repo.get_by_slug = AsyncMock(return_value=None)
        repo.get_by_id = AsyncMock(return_value=None)
        repo.create = AsyncMock()
        repo.delete = AsyncMock(return_value=True)
        repo.list_with_filters = AsyncMock(return_value=[])
        repo.get_categories = AsyncMock(return_value=["tech", "news"])
        repo.increment_views = AsyncMock()
        return repo

    @pytest.fixture
    def article_service(self, mock_db, mock_repo):
        """Create ArticleService with mocked dependencies."""
        service = ArticleService(mock_db)
        service.repo = mock_repo
        return service

    @pytest.mark.asyncio
    async def test_create_article_success(self, article_service, mock_repo):
        """Test creating article with valid data."""
        # Arrange
        mock_article = MagicMock()
        mock_article.id = "article-123"
        mock_article.slug = "test-article"
        mock_repo.create.return_value = mock_article

        # Act
        result = await article_service.create_article(
            title="Test Article",
            content="Test content here",
            author="testuser"
        )

        # Assert
        assert result.id == "article-123"
        assert result.slug == "test-article"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_article_unique_slug(self, article_service, mock_repo):
        """Test that duplicate slugs get timestamp suffix."""
        # Arrange - simulate existing article with same slug
        existing_article = MagicMock()
        mock_repo.get_by_slug.return_value = existing_article

        mock_article = MagicMock()
        mock_article.id = "article-456"
        mock_repo.create.return_value = mock_article

        # Act
        with patch('app.services.article_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 1, 15, 10, 30)
            mock_datetime.utcnow.return_value = datetime(2025, 1, 15, 10, 30)
            await article_service.create_article(
                title="Test Article",
                content="Content",
                author="testuser"
            )

        # Assert - check that slug was modified
        call_args = mock_repo.create.call_args[0][0]
        assert "202501151030" in call_args["slug"]

    @pytest.mark.asyncio
    async def test_create_article_with_published_status(self, article_service, mock_repo):
        """Test creating article with published status sets published_at."""
        # Arrange
        mock_article = MagicMock()
        mock_repo.create.return_value = mock_article

        # Act
        await article_service.create_article(
            title="Published Article",
            content="Content",
            author="testuser",
            status="published"
        )

        # Assert
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["status"] == "published"
        assert call_args["published_at"] is not None

    @pytest.mark.asyncio
    async def test_get_article_increments_views(self, article_service, mock_repo):
        """Test getting article increments view counter."""
        # Arrange
        mock_article = MagicMock()
        mock_article.id = "article-123"
        mock_repo.get_by_slug.return_value = mock_article

        # Act
        result = await article_service.get_article("test-slug")

        # Assert
        assert result == mock_article
        mock_repo.increment_views.assert_called_once_with(mock_article)

    @pytest.mark.asyncio
    async def test_get_article_not_found(self, article_service, mock_repo):
        """Test getting non-existent article returns None."""
        # Arrange
        mock_repo.get_by_slug.return_value = None

        # Act
        result = await article_service.get_article("nonexistent-slug")

        # Assert
        assert result is None
        mock_repo.increment_views.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_articles_with_tag_filter(self, article_service, mock_repo):
        """Test listing articles filters by tag."""
        # Arrange
        article1 = MagicMock()
        article1.id = "1"
        article1.title = "Article 1"
        article1.slug = "article-1"
        article1.excerpt = "Excerpt 1"
        article1.category = "tech"
        article1.tags = ["python", "testing"]
        article1.status = "published"
        article1.author = "user1"
        article1.created_at = datetime(2025, 1, 15)
        article1.views = 10

        article2 = MagicMock()
        article2.id = "2"
        article2.title = "Article 2"
        article2.slug = "article-2"
        article2.excerpt = "Excerpt 2"
        article2.category = "tech"
        article2.tags = ["javascript"]
        article2.status = "published"
        article2.author = "user2"
        article2.created_at = datetime(2025, 1, 14)
        article2.views = 5

        mock_repo.list_with_filters.return_value = [article1, article2]

        # Act
        result = await article_service.list_articles(tag="python")

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_get_categories(self, article_service, mock_repo):
        """Test getting unique categories."""
        # Act
        result = await article_service.get_categories()

        # Assert
        assert result == ["tech", "news"]
        mock_repo.get_categories.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_article_success(self, article_service, mock_repo, mock_db):
        """Test updating article fields."""
        # Arrange
        mock_article = MagicMock()
        mock_article.id = "article-123"
        mock_article.title = "Original Title"
        mock_article.published_at = None
        mock_repo.get_by_id.return_value = mock_article

        # Act
        result = await article_service.update_article(
            "article-123",
            title="Updated Title"
        )

        # Assert
        assert result == mock_article
        assert mock_article.title == "Updated Title"
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_article_not_found(self, article_service, mock_repo):
        """Test updating non-existent article returns None."""
        # Arrange
        mock_repo.get_by_id.return_value = None

        # Act
        result = await article_service.update_article(
            "nonexistent-id",
            title="New Title"
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_article_sets_published_at(self, article_service, mock_repo, mock_db):
        """Test publishing article sets published_at."""
        # Arrange
        mock_article = MagicMock()
        mock_article.published_at = None
        mock_repo.get_by_id.return_value = mock_article

        # Act
        await article_service.update_article(
            "article-123",
            status="published"
        )

        # Assert
        assert mock_article.published_at is not None

    @pytest.mark.asyncio
    async def test_delete_article_success(self, article_service, mock_repo, mock_db):
        """Test deleting article."""
        # Arrange
        mock_repo.delete.return_value = True

        # Act
        result = await article_service.delete_article("article-123")

        # Assert
        assert result is True
        mock_repo.delete.assert_called_once_with("article-123")
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_article_not_found(self, article_service, mock_repo, mock_db):
        """Test deleting non-existent article."""
        # Arrange
        mock_repo.delete.return_value = False

        # Act
        result = await article_service.delete_article("nonexistent-id")

        # Assert
        assert result is False
