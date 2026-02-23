"""Storage service for S3-compatible object storage (MinIO)."""

import io
import logging
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ImageUploadResult:
    """Result of image upload operation."""

    object_key: str
    url: str
    filename: str
    size_bytes: int
    width: int | None
    height: int | None
    content_type: str


class StorageService:
    """S3-compatible storage service for article images."""

    def __init__(self) -> None:
        protocol = "https" if settings.minio_use_ssl else "http"
        self.client = boto3.client(
            "s3",
            endpoint_url=f"{protocol}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self.bucket = settings.minio_bucket

    def upload_image(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        project_id: str,
    ) -> ImageUploadResult:
        """Validate, resize if needed, upload image to S3."""
        self._validate_image(file_content, content_type)

        width: int | None = None
        height: int | None = None

        # SVG: skip Pillow processing
        if content_type == "image/svg+xml":
            final_content = file_content
        else:
            final_content, width, height = self._process_image(
                file_content, settings.image_max_dimension
            )

        object_key = self._generate_key(filename, project_id)

        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=final_content,
            ContentType=content_type,
        )

        url = f"/api/articles/images/{object_key}"

        return ImageUploadResult(
            object_key=object_key,
            url=url,
            filename=filename,
            size_bytes=len(final_content),
            width=width,
            height=height,
            content_type=content_type,
        )

    def delete_image(self, object_key: str) -> bool:
        """Delete image from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {object_key}: {e}")
            return False

    def get_image(self, object_key: str) -> tuple[bytes, str]:
        """Get image content and content type from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            content = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            return content, content_type
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise FileNotFoundError(f"Image not found: {object_key}") from e
            raise

    def _validate_image(self, content: bytes, content_type: str) -> None:
        """Validate image type, size, and integrity."""
        if not content:
            raise ValueError("Empty file")

        max_bytes = settings.max_image_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(
                f"File too large: {len(content)} bytes "
                f"(max {settings.max_image_size_mb} MB)"
            )

        if content_type not in settings.allowed_image_types:
            raise ValueError(f"Unsupported image format: {content_type}")

        # Validate with Pillow (skip SVG)
        if content_type != "image/svg+xml":
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
            except Exception as e:
                raise ValueError("Invalid image file") from e

    def _process_image(
        self, content: bytes, max_dim: int
    ) -> tuple[bytes, int, int]:
        """Open image, resize if needed, return (bytes, width, height)."""
        img = Image.open(io.BytesIO(content))
        width, height = img.size

        # Resize if exceeds max dimension
        if width > max_dim or height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.LANCZOS)
            width, height = img.size

        buf = io.BytesIO()
        img_format = img.format or "PNG"
        save_kwargs: dict = {}
        if img_format == "JPEG":
            save_kwargs["quality"] = 85
        img.save(buf, format=img_format, **save_kwargs)
        return buf.getvalue(), width, height

    def _generate_key(self, filename: str, project_id: str) -> str:
        """Generate unique S3 key: {project_id}/{uuid}.{ext}."""
        ext = PurePosixPath(filename).suffix.lstrip(".").lower() or "png"
        unique_id = uuid.uuid4().hex[:12]
        return f"{project_id}/{unique_id}.{ext}"
