"""Article import service — parse MD/DOCX files into articles."""

import logging
import re
from io import BytesIO

import mammoth
import markdownify
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article
from app.services.article_service import ArticleService

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".md", ".docx"}


class ArticleImportService:
    """Service for importing articles from MD/DOCX files."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.article_service = ArticleService(db)

    async def import_from_file(
        self,
        file: UploadFile,
        folder_id: str | None,
        project_id: str,
        author: str,
        created_by: str,
        category: str | None = None,
        status: str = "draft",
        tags: list[str] | None = None,
    ) -> tuple[Article, list[str]]:
        """Import file and create article. Returns (article, warnings)."""
        content_bytes, ext, warnings = await self._read_and_validate(file)

        if ext == ".md":
            title, markdown = self._parse_markdown(content_bytes)
        else:
            title, markdown = self._parse_docx(content_bytes, warnings)

        markdown = self._sanitize_content(markdown)

        article = await self.article_service.create_article(
            title=title,
            content=markdown,
            author=author,
            category=category,
            tags=tags or [],
            status=status,
            project_id=project_id,
            created_by=created_by,
            folder_id=folder_id,
        )

        return article, warnings

    async def preview_file(
        self, file: UploadFile
    ) -> tuple[str, str, list[str]]:
        """Parse file and return (title, content, warnings) without creating article."""
        content_bytes, ext, warnings = await self._read_and_validate(file)

        if ext == ".md":
            title, markdown = self._parse_markdown(content_bytes)
        else:
            title, markdown = self._parse_docx(content_bytes, warnings)

        markdown = self._sanitize_content(markdown)
        return title, markdown, warnings

    async def _read_and_validate(
        self, file: UploadFile
    ) -> tuple[bytes, str, list[str]]:
        """Read file bytes and validate extension/size. Returns (bytes, ext, warnings)."""
        warnings: list[str] = []

        filename = file.filename or ""
        ext = ""
        dot_idx = filename.rfind(".")
        if dot_idx >= 0:
            ext = filename[dot_idx:].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: '{ext}'. Allowed: .md, .docx",
            )

        content_bytes = await file.read()

        if len(content_bytes) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        if len(content_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(content_bytes)} bytes. Max: {MAX_FILE_SIZE} bytes (5 MB)",
            )

        return content_bytes, ext, warnings

    def _parse_markdown(self, content: bytes) -> tuple[str, str]:
        """Parse MD file bytes into (title, content)."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        # Remove BOM
        if text.startswith("\ufeff"):
            text = text[1:]

        title = self._extract_title(text)
        return title, text

    def _parse_docx(
        self, content: bytes, warnings: list[str]
    ) -> tuple[str, str]:
        """Parse DOCX file bytes into (title, markdown)."""
        try:
            result = mammoth.convert_to_html(BytesIO(content))
        except Exception as e:
            logger.error("Failed to parse DOCX: %s", e)
            warnings.append(f"Failed to parse DOCX: {str(e)}")
            return "Imported Document", ""

        html = result.value

        for msg in result.messages:
            if "image" in str(msg).lower():
                if "Images were skipped during import" not in warnings:
                    warnings.append("Images were skipped during import")
            else:
                logger.warning("mammoth: %s", msg)

        try:
            markdown = markdownify.markdownify(
                html,
                heading_style="ATX",
                bullets="-",
                strip=["img"],
            )
        except Exception as e:
            logger.error("Failed to convert DOCX HTML to markdown: %s", e)
            warnings.append(f"Failed to convert to markdown: {str(e)}")
            return "Imported Document", html

        title = self._extract_title(markdown)
        return title, markdown

    def _extract_title(self, markdown: str) -> str:
        """Extract title from first # heading or first non-empty line."""
        for line in markdown.split("\n"):
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^#\s+(.+)$", line)
            if match:
                return match.group(1).strip()
            return line[:200]
        return "Untitled"

    def _sanitize_content(self, markdown: str) -> str:
        """Remove potentially dangerous HTML, normalize newlines."""
        # Remove script/iframe/style tags
        markdown = re.sub(
            r"<(script|iframe|style)[^>]*>.*?</\1>",
            "",
            markdown,
            flags=re.DOTALL | re.IGNORECASE,
        )
        markdown = re.sub(
            r"<(script|iframe|style)[^>]*/?>",
            "",
            markdown,
            flags=re.IGNORECASE,
        )
        # Normalize line endings
        markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
        # Remove excessive blank lines (3+ → 2)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)
        return markdown.strip()
