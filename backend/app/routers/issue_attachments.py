"""Issue attachments router."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import IssueAttachment
from app.models.user import User

router = APIRouter(prefix="/api/v1/attachments", tags=["attachments"])


@router.get("/issues/{issue_id}")
async def list_attachments(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List attachments for an issue."""
    q = select(IssueAttachment).where(IssueAttachment.issue_id == issue_id).order_by(IssueAttachment.created_at.desc())
    result = await db.execute(q)
    return [
        {
            "id": a.id, "filename": a.filename, "content_type": a.content_type,
            "size_bytes": a.size_bytes, "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


@router.post("/issues/{issue_id}")
async def upload_attachment(
    issue_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Upload an attachment to an issue."""
    from app.services.storage_service import StorageService

    storage = StorageService()
    content = await file.read()
    object_key = f"attachments/{issue_id}/{file.filename}"
    await storage.upload(object_key, content, file.content_type or "application/octet-stream")
    att = IssueAttachment(
        issue_id=issue_id, object_key=object_key, filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content), uploaded_by=user.id,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return {"id": att.id, "filename": att.filename, "message": "Attachment uploaded"}


@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete an attachment."""
    att = await db.get(IssueAttachment, attachment_id)
    if not att:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await db.delete(att)
    await db.commit()
    return {"message": "Attachment deleted"}
