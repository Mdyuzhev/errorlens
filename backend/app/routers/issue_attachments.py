"""Issue attachments API router."""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import IssueAttachment
from app.models.user import User
from app.repositories.attachment_repo import IssueAttachmentRepository
from app.repositories.task_repo import TaskRepository
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

router = APIRouter(prefix="/api/v1/issues", tags=["attachments"])


@router.post("/{issue_id}/attachments")
async def upload_attachment(
    issue_id: str,
    file: UploadFile,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload file attachment to a task."""
    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(issue_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    storage = StorageService()
    result = storage.upload_file(
        content=content,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
        prefix=f"attachments/{issue_id}",
    )

    repo = IssueAttachmentRepository(db)
    attachment = await repo.create({
        "issue_id": issue_id,
        "object_key": result["object_key"],
        "filename": result["filename"],
        "content_type": result["content_type"],
        "size_bytes": result["size_bytes"],
        "uploaded_by": user.id,
    })
    await db.commit()

    return _serialize(attachment)


@router.get("/{issue_id}/attachments")
async def list_attachments(
    issue_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List attachments for a task."""
    repo = IssueAttachmentRepository(db)
    items = await repo.list_by_issue(issue_id)
    return [_serialize(a) for a in items]


@router.delete("/{issue_id}/attachments/{attachment_id}")
async def delete_attachment(
    issue_id: str,
    attachment_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete attachment from MinIO and DB."""
    repo = IssueAttachmentRepository(db)
    attachment = await repo.get_by_id(attachment_id)
    if not attachment or attachment.issue_id != issue_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    storage = StorageService()
    storage.delete_image(attachment.object_key)

    await repo.delete(attachment_id)
    await db.commit()

    return {"ok": True}


def _serialize(a: IssueAttachment) -> dict:
    return {
        "id": a.id,
        "issue_id": a.issue_id,
        "object_key": a.object_key,
        "filename": a.filename,
        "content_type": a.content_type,
        "size_bytes": a.size_bytes,
        "uploaded_by": a.uploaded_by,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
