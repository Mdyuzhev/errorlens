"""Notifications API router."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.db_models import Notification
from app.models.user import User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get last 50 notifications for current user."""
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "entity_type": n.entity_type,
            "entity_id": n.entity_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get count of unread notifications."""
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    count = result.scalar() or 0
    return {"count": count}


@router.post("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    return {"message": "ok"}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark all notifications as read for current user."""
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "ok"}
