"""Articles/Knowledge base CRUD router - thin controller.

Multi-tenancy: Articles are filtered by project_id.
Users can only access articles in projects they own or are members of.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import (
    check_project_access,
    get_default_project,
    require_auth,
)
from app.models.user import User
from app.repositories.article_version_repo import ArticleVersionRepository
from app.services.article_import_service import ArticleImportService
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleCreate(BaseModel):
    title: str
    content: str
    excerpt: str | None = None
    category: str | None = None
    tags: list[str] = []
    status: str = "draft"
    project_id: str | None = None  # Required for multi-tenancy
    folder_id: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    excerpt: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class BreadcrumbItem(BaseModel):
    id: str
    name: str
    type: str  # 'root' | 'folder' | 'article'


class VersionListItem(BaseModel):
    id: str
    title: str
    saved_by: str | None
    created_at: str


class VersionDetail(BaseModel):
    id: str
    title: str
    content: str
    saved_by: str | None
    created_at: str


@router.get("")
async def list_articles(
    q: str | None = Query(default=None, description="Search query"),
    project_id: str | None = Query(default=None, description="Filter by project ID"),
    folder_id: str | None = Query(default=None, description="Filter by folder ID"),
    category: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    List articles with filters.

    If project_id provided, filters by that project (requires access).
    If project_id is None, returns articles from user's default project.
    """
    # Determine which project to use
    if project_id:
        await check_project_access(project_id, user, db)
        filter_project_id = project_id
    else:
        default_project = await get_default_project(user, db)
        filter_project_id = default_project.id if default_project else None

    service = ArticleService(db)
    if q:
        return await service.search_articles(q, project_id=filter_project_id, limit=10)
    return await service.list_articles(
        project_id=filter_project_id,
        category=category,
        status=status,
        tag=tag,
        folder_id=folder_id,
    )


@router.get("/categories/list")
async def list_categories(
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get unique categories for a project."""
    if project_id:
        await check_project_access(project_id, user, db)
        filter_project_id = project_id
    else:
        default_project = await get_default_project(user, db)
        filter_project_id = default_project.id if default_project else None

    service = ArticleService(db)
    return await service.get_categories(project_id=filter_project_id)


@router.post("/import")
async def import_article(
    file: UploadFile = File(...),
    folder_id: str | None = Form(default=None),
    category: str | None = Form(default=None),
    status: str = Form(default="draft"),
    tags: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Import article from .md or .docx file (quick import as draft)."""
    # Determine project
    default_project = await get_default_project(user, db)
    if not default_project:
        raise HTTPException(
            status_code=400, detail="No default project found"
        )
    project_id = default_project.id

    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    service = ArticleImportService(db)
    article, warnings = await service.import_from_file(
        file=file,
        folder_id=folder_id,
        project_id=project_id,
        author=user.username,
        created_by=user.id,
        category=category,
        status=status,
        tags=tags_list,
    )

    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "content_length": len(article.content or ""),
        "warnings": warnings,
    }


@router.post("/import/preview")
async def import_article_preview(
    file: UploadFile = File(...),
    _user: User = Depends(require_auth),
):
    """Parse file and return title + content without creating article."""
    service = ArticleImportService(None)  # type: ignore[arg-type]
    title, content, warnings = await service.preview_file(file)

    return {
        "title": title,
        "content": content,
        "warnings": warnings,
    }


@router.get("/{article_id}")
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Get article by ID.

    Returns 404 if not found or user has no access to article's project.
    """
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check project access
    if article.project_id:
        await check_project_access(article.project_id, user, db)

    return service.to_detail_dict(article)


@router.post("")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Create new article.

    Requires member role or higher in the project.
    """
    # Determine project
    if data.project_id:
        await check_project_access(data.project_id, user, db, required_role="member")
        project_id = data.project_id
    else:
        default_project = await get_default_project(user, db)
        if not default_project:
            raise HTTPException(
                status_code=400, detail="No project specified and no default project found"
            )
        project_id = default_project.id

    service = ArticleService(db)
    article = await service.create_article(
        title=data.title,
        content=data.content,
        author=user.username,
        excerpt=data.excerpt,
        category=data.category,
        tags=data.tags,
        status=data.status,
        project_id=project_id,
        created_by=user.id,
        folder_id=data.folder_id,
    )
    return {"id": article.id, "slug": article.slug}


@router.put("/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Update article.

    Requires member role or higher in the article's project.
    """
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check project access with member role
    if article.project_id:
        await check_project_access(article.project_id, user, db, required_role="member")

    updated = await service.update_article(article_id, **data.model_dump(exclude_unset=True))

    if not updated:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article updated"}


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """
    Delete article.

    Requires admin role or higher in the article's project.
    """
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Check project access with admin role for delete
    if article.project_id:
        await check_project_access(article.project_id, user, db, required_role="admin")

    deleted = await service.delete_article(article_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"message": "Article deleted"}


@router.get("/{article_id}/breadcrumbs")
async def get_article_breadcrumbs(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get breadcrumb trail for an article: root → folders → article."""
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.project_id:
        await check_project_access(article.project_id, user, db)

    return await service.get_breadcrumbs(article_id)


@router.get("/{article_id}/export/pdf")
async def export_article_pdf(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Export article as PDF via weasyprint."""
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.project_id:
        await check_project_access(article.project_id, user, db)

    breadcrumbs = await service.get_breadcrumbs(article_id)
    crumb_path = " / ".join(b["name"] for b in breadcrumbs)
    body_html = _render_article_content(article.content)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html_content = (
        "<html><head><meta charset='utf-8'>"
        "<style>body{font-family:sans-serif;margin:40px;}"
        "pre{background:#f4f4f4;padding:12px;border-radius:4px;}"
        ".callout{border-left:4px solid #888;padding:8px 12px;margin:8px 0;}"
        "h1,h2,h3{margin-top:16px;}</style></head><body>"
        f"<p style='color:#888;font-size:12px'>{crumb_path}</p>"
        f"<h1>{article.title}</h1>"
        f"<p style='color:#888;font-size:11px'>Generated: {now}</p><hr>"
        f"{body_html}"
        "</body></html>"
    )

    import weasyprint  # noqa: E402

    pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{article.slug}.pdf"'},
    )


@router.get("/{article_id}/versions")
async def list_article_versions(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List all versions of an article, newest first."""
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.project_id:
        await check_project_access(article.project_id, user, db)

    version_repo = ArticleVersionRepository(db)
    versions = await version_repo.list_by_article(article_id)
    return [
        {
            "id": v.id,
            "title": v.title,
            "saved_by": v.saved_by,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


@router.get("/{article_id}/versions/{version_id}")
async def get_article_version(
    article_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get a specific version of an article."""
    service = ArticleService(db)
    article = await service.get_article_by_id(article_id)

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.project_id:
        await check_project_access(article.project_id, user, db)

    version_repo = ArticleVersionRepository(db)
    version = await version_repo.get_by_id_and_article(version_id, article_id)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "id": version.id,
        "title": version.title,
        "content": version.content,
        "saved_by": version.saved_by,
        "created_at": version.created_at.isoformat(),
    }


def _extract_text_from_nodes(nodes: list[dict]) -> str:
    """Recursively extract text from TipTap JSON nodes."""
    parts: list[str] = []
    for node in nodes:
        node_type = node.get("type", "")
        if node_type == "text":
            parts.append(node.get("text", ""))
        elif node_type == "hardBreak":
            parts.append("<br>")
        elif node_type in ("heading", "paragraph", "blockquote", "listItem"):
            tag = {
                "heading": f"h{node.get('attrs', {}).get('level', 2)}",
                "paragraph": "p",
                "blockquote": "blockquote",
                "listItem": "li",
            }[node_type]
            inner = _extract_text_from_nodes(node.get("content", []))
            parts.append(f"<{tag}>{inner}</{tag}>")
        elif node_type == "bulletList":
            inner = _extract_text_from_nodes(node.get("content", []))
            parts.append(f"<ul>{inner}</ul>")
        elif node_type == "orderedList":
            inner = _extract_text_from_nodes(node.get("content", []))
            parts.append(f"<ol>{inner}</ol>")
        elif node_type == "codeBlock":
            inner = _extract_text_from_nodes(node.get("content", []))
            parts.append(f"<pre><code>{inner}</code></pre>")
        elif node_type == "callout":
            attrs = node.get("attrs", {})
            kind = attrs.get("type", "info").capitalize()
            inner = _extract_text_from_nodes(node.get("content", []))
            parts.append(
                f'<div class="callout"><strong>[{kind}]</strong> {inner}</div>'
            )
        elif node_type == "expand":
            attrs = node.get("attrs", {})
            summary = attrs.get("summary", "Details")
            inner = _extract_text_from_nodes(node.get("content", []))
            parts.append(f"<details open><summary>{summary}</summary>{inner}</details>")
        elif "content" in node:
            parts.append(_extract_text_from_nodes(node["content"]))
    return "".join(parts)


def _render_article_content(content_raw: str) -> str:
    """Parse grid-1 article content JSON and render to HTML."""
    try:
        data = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
    except (json.JSONDecodeError, TypeError):
        return f"<p>{content_raw or ''}</p>"

    if isinstance(data, dict) and data.get("type") == "doc":
        return _extract_text_from_nodes(data.get("content", []))

    # Grid-1 format: {rows: [{columns: [{content: {...}}]}]}
    rows = data.get("rows", []) if isinstance(data, dict) else []
    if not rows:
        return f"<p>{content_raw or ''}</p>"

    parts: list[str] = []
    for row in rows:
        for col in row.get("columns", []):
            col_content = col.get("content")
            if not col_content:
                continue
            if isinstance(col_content, dict) and col_content.get("type") == "doc":
                parts.append(_extract_text_from_nodes(col_content.get("content", [])))
            elif isinstance(col_content, str):
                parts.append(f"<p>{col_content}</p>")
    return "".join(parts) if parts else f"<p>{content_raw or ''}</p>"
