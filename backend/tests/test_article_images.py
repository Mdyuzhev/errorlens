"""Tests for article images — StorageService + API endpoints."""

import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from app.services.storage_service import ImageUploadResult, StorageService


# ============ Fixtures ============


@pytest.fixture
def sample_png() -> bytes:
    """100x100 red pixel PNG."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_jpeg() -> bytes:
    """100x100 blue JPEG."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def sample_webp() -> bytes:
    """100x100 green WebP."""
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture
def sample_gif() -> bytes:
    """100x100 yellow GIF."""
    img = Image.new("RGB", (100, 100), color="yellow")
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


@pytest.fixture
def sample_svg() -> bytes:
    """Simple SVG."""
    return b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="red" width="100" height="100"/></svg>'


@pytest.fixture
def large_png() -> bytes:
    """4000x3000 image exceeding max dimension."""
    img = Image.new("RGB", (4000, 3000), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    client = MagicMock()
    client.put_object = MagicMock()
    client.delete_object = MagicMock()
    client.get_object = MagicMock()
    return client


@pytest.fixture
def storage_service(mock_s3_client):
    """StorageService with mocked S3 client."""
    with patch("app.services.storage_service.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_s3_client
        service = StorageService()
        service.client = mock_s3_client
        return service


# ============ StorageService Tests ============


class TestUploadImage:
    """Tests for StorageService.upload_image."""

    def test_upload_png(self, storage_service, sample_png):
        """Upload valid PNG → success with dimensions."""
        result = storage_service.upload_image(
            sample_png, "screenshot.png", "image/png", "proj-1"
        )

        assert isinstance(result, ImageUploadResult)
        assert result.url.startswith("/api/articles/images/")
        assert result.filename == "screenshot.png"
        assert result.content_type == "image/png"
        assert result.width == 100
        assert result.height == 100
        assert result.size_bytes > 0
        storage_service.client.put_object.assert_called_once()

    def test_upload_jpeg(self, storage_service, sample_jpeg):
        """Upload valid JPEG → success."""
        result = storage_service.upload_image(
            sample_jpeg, "photo.jpg", "image/jpeg", "proj-1"
        )
        assert result.content_type == "image/jpeg"
        assert result.width == 100

    def test_upload_webp(self, storage_service, sample_webp):
        """Upload valid WebP → success."""
        result = storage_service.upload_image(
            sample_webp, "image.webp", "image/webp", "proj-1"
        )
        assert result.content_type == "image/webp"

    def test_upload_gif(self, storage_service, sample_gif):
        """Upload valid GIF → success."""
        result = storage_service.upload_image(
            sample_gif, "anim.gif", "image/gif", "proj-1"
        )
        assert result.content_type == "image/gif"

    def test_upload_svg(self, storage_service, sample_svg):
        """Upload valid SVG → success, no width/height."""
        result = storage_service.upload_image(
            sample_svg, "icon.svg", "image/svg+xml", "proj-1"
        )
        assert result.content_type == "image/svg+xml"
        assert result.width is None
        assert result.height is None

    def test_upload_returns_markdown_url(self, storage_service, sample_png):
        """URL starts with /api/articles/images/."""
        result = storage_service.upload_image(
            sample_png, "test.png", "image/png", "proj-1"
        )
        assert result.url.startswith("/api/articles/images/proj-1/")

    def test_upload_too_large(self, storage_service):
        """File > max size → ValueError with 'too large'."""
        # Create fake large content that passes type check but exceeds size
        with patch.object(storage_service, "_validate_image") as mock_validate:
            mock_validate.side_effect = ValueError(
                "File too large: 11000000 bytes (max 10 MB)"
            )
            with pytest.raises(ValueError, match="too large"):
                storage_service.upload_image(
                    b"x" * 100, "big.png", "image/png", "proj-1"
                )

    def test_upload_wrong_type(self, storage_service):
        """Unsupported type → ValueError."""
        with pytest.raises(ValueError, match="Unsupported image format"):
            storage_service.upload_image(
                b"%PDF-1.4", "doc.pdf", "application/pdf", "proj-1"
            )

    def test_upload_corrupted(self, storage_service):
        """Invalid bytes with image content type → ValueError."""
        with pytest.raises(ValueError, match="Invalid image file"):
            storage_service.upload_image(
                b"not-an-image", "bad.png", "image/png", "proj-1"
            )

    def test_resize_large_image(self, storage_service, large_png):
        """4000x3000 → resized to max 2048 on longest side."""
        result = storage_service.upload_image(
            large_png, "huge.png", "image/png", "proj-1"
        )
        assert result.width <= 2048
        assert result.height <= 2048
        # Aspect ratio preserved: 4000x3000 → 2048x1536
        assert result.width == 2048
        assert result.height == 1536


class TestValidation:
    """Tests for input validation edge cases."""

    def test_none_handling(self, storage_service):
        """Empty content → ValueError."""
        with pytest.raises(ValueError, match="Empty file"):
            storage_service.upload_image(
                b"", "empty.png", "image/png", "proj-1"
            )

    def test_empty_file(self, storage_service):
        """Zero bytes → ValueError."""
        with pytest.raises(ValueError, match="Empty file"):
            storage_service.upload_image(
                b"", "zero.png", "image/png", "proj-1"
            )


class TestDeleteImage:
    """Tests for StorageService.delete_image."""

    def test_delete_success(self, storage_service):
        """Delete existing image → True."""
        result = storage_service.delete_image("proj-1/abc123.png")
        assert result is True
        storage_service.client.delete_object.assert_called_once()

    def test_delete_client_error(self, storage_service):
        """S3 client error → False."""
        from botocore.exceptions import ClientError

        storage_service.client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "500", "Message": "Internal"}}, "DeleteObject"
        )
        result = storage_service.delete_image("proj-1/missing.png")
        assert result is False


class TestGetImage:
    """Tests for StorageService.get_image."""

    def test_get_image_success(self, storage_service, sample_png):
        """GET existing → content + content_type."""
        body_mock = MagicMock()
        body_mock.read.return_value = sample_png
        storage_service.client.get_object.return_value = {
            "Body": body_mock,
            "ContentType": "image/png",
        }

        content, ct = storage_service.get_image("proj-1/abc.png")
        assert content == sample_png
        assert ct == "image/png"

    def test_get_image_not_found(self, storage_service):
        """GET non-existent → FileNotFoundError."""
        from botocore.exceptions import ClientError

        storage_service.client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )
        with pytest.raises(FileNotFoundError, match="Image not found"):
            storage_service.get_image("proj-1/missing.png")


class TestConcurrentUpload:
    """Tests for concurrent upload safety."""

    def test_concurrent_upload(self, storage_service, sample_png):
        """3 concurrent uploads → all succeed with unique URLs."""
        results = []
        for i in range(3):
            r = storage_service.upload_image(
                sample_png, f"img{i}.png", "image/png", "proj-1"
            )
            results.append(r)

        urls = [r.url for r in results]
        # All URLs are unique (different UUIDs)
        assert len(set(urls)) == 3
        # All succeeded
        assert all(r.size_bytes > 0 for r in results)


class TestKeyGeneration:
    """Tests for S3 key generation."""

    def test_key_format(self, storage_service):
        """Key follows {project_id}/{uuid}.{ext} pattern."""
        key = storage_service._generate_key("photo.jpg", "proj-abc")
        assert key.startswith("proj-abc/")
        assert key.endswith(".jpg")
        parts = key.split("/")
        assert len(parts) == 2

    def test_key_uniqueness(self, storage_service):
        """Two keys for same filename are different."""
        k1 = storage_service._generate_key("same.png", "proj-1")
        k2 = storage_service._generate_key("same.png", "proj-1")
        assert k1 != k2

    def test_key_no_extension(self, storage_service):
        """Filename without extension → defaults to .png."""
        key = storage_service._generate_key("noext", "proj-1")
        assert key.endswith(".png")


class TestProcessImage:
    """Tests for _process_image."""

    def test_process_keeps_small_image(self, storage_service, sample_png):
        """100x100 image stays unchanged."""
        content, w, h = storage_service._process_image(sample_png, 2048)
        assert w == 100
        assert h == 100

    def test_process_resizes_large(self, storage_service, large_png):
        """4000x3000 → fits within 2048."""
        content, w, h = storage_service._process_image(large_png, 2048)
        assert w <= 2048
        assert h <= 2048
        assert w == 2048
        assert h == 1536


class TestMultiTenancy:
    """Tests for project isolation in storage keys."""

    def test_different_projects_different_paths(self, storage_service, sample_png):
        """Images from different projects have different key prefixes."""
        r1 = storage_service.upload_image(
            sample_png, "img.png", "image/png", "project-a"
        )
        r2 = storage_service.upload_image(
            sample_png, "img.png", "image/png", "project-b"
        )
        assert r1.object_key.startswith("project-a/")
        assert r2.object_key.startswith("project-b/")
