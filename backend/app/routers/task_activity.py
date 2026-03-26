"""Task activity feed and comments — split from tasks.py (EL031)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: str


# ---- Activity Feed ----

@router.get("/{task_id}/activity")
async def get_activity(
    task_id: str,
    limit: int = Query(default=20, le=100),
    before: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get combined activity feed (comments + activities)."""
    from datetime import datetime as dt

    from sqlalchemy import literal_column, select, union_all
    from sqlalchemy.orm import joinedload

    from app.models.db_models import TaskActivity, TaskComment

    before_dt = None
    if before:
        try:
            before_dt = dt.fromisoformat(before)
        except ValueError:
            pass

    comments_q = (
        select(TaskComment.id, TaskComment.created_at, literal_column("'comment'").label("entry_type"))
        .where(TaskComment.task_id == task_id)
    )
    if before_dt:
        comments_q = comments_q.where(TaskComment.created_at < before_dt)

    activities_q = (
        select(TaskActivity.id, TaskActivity.created_at, literal_column("'activity'").label("entry_type"))
        .where(TaskActivity.task_id == task_id)
    )
    if before_dt:
        activities_q = activities_q.where(TaskActivity.created_at < before_dt)

    combined = union_all(comments_q, activities_q).subquery()
    final_q = select(combined.c.id, combined.c.entry_type).order_by(combined.c.created_at.desc()).limit(limit)
    result = await db.execute(final_q)
    entries = result.all()

    comment_ids = [eid for eid, etype in entries if etype == "comment"]
    activity_ids = [eid for eid, etype in entries if etype == "activity"]

    comments_map = {}
    if comment_ids:
        res = await db.execute(
            select(TaskComment).options(joinedload(TaskComment.author)).where(TaskComment.id.in_(comment_ids))
        )
        comments_map = {c.id: c for c in res.unique().scalars()}

    activities_map = {}
    if activity_ids:
        res = await db.execute(
            select(TaskActivity).options(joinedload(TaskActivity.actor)).where(TaskActivity.id.in_(activity_ids))
        )
        activities_map = {a.id: a for a in res.unique().scalars()}

    feed = []
    for entry_id, entry_type in entries:
        if entry_type == "comment":
            comment = comments_map.get(entry_id)
            if comment:
                feed.append({
                    "entry_type": "comment", "id": comment.id,
                    "content": comment.content, "is_edited": comment.is_edited,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                    "author": {
                        "id": comment.author.id, "username": comment.author.username,
                        "display_name": comment.author.display_name,
                    } if comment.author else None,
                })
        else:
            activity = activities_map.get(entry_id)
            if activity:
                feed.append({
                    "entry_type": "activity", "id": activity.id,
                    "action_type": activity.action_type, "field_name": activity.field_name,
                    "old_value": activity.old_value, "new_value": activity.new_value,
                    "created_at": activity.created_at.isoformat(),
                    "actor": {
                        "id": activity.actor.id, "username": activity.actor.username,
                        "display_name": activity.actor.display_name,
                    } if activity.actor else None,
                })
    return feed


# ---- Comments ----

@router.post("/{task_id}/comments")
async def create_comment(
    task_id: str,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a comment on a task."""
    from app.models.db_models import TaskComment
    service = TaskService(db)

    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comment = TaskComment(task_id=task_id, author_id=user.id, content=data.content)
    db.add(comment)
    await service._record_activity(task_id, user.id, "commented", new_value={"comment_id": comment.id})
    await db.commit()
    await db.refresh(comment)

    return {
        "id": comment.id, "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "author": {"id": user.id, "username": user.username, "display_name": user.display_name},
    }


@router.put("/{task_id}/comments/{comment_id}")
async def update_comment(
    task_id: str,
    comment_id: str,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Edit a comment (only author or admin)."""
    from sqlalchemy import select
    from app.models.db_models import TaskComment

    result = await db.execute(
        select(TaskComment).where(TaskComment.id == comment_id, TaskComment.task_id == task_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to edit this comment")

    comment.content = data.content
    comment.is_edited = True
    comment.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Comment updated"}


@router.delete("/{task_id}/comments/{comment_id}")
async def delete_comment(
    task_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete a comment (only author or admin)."""
    from sqlalchemy import delete, select
    from app.models.db_models import TaskComment

    result = await db.execute(
        select(TaskComment).where(TaskComment.id == comment_id, TaskComment.task_id == task_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

    await db.execute(delete(TaskComment).where(TaskComment.id == comment_id))
    await db.commit()
    return {"message": "Comment deleted"}
