"""Tasks CRUD router with Kanban board support - thin controller."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.jql import JQLCompiler, JQLContext, JQLError, JQLSyntaxError
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.exceptions import TaskDepthExceededError
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    assignee: str | None = None
    assignee_id: str | None = None
    labels: list[str] = []
    due_date: datetime | None = None
    session_id: str | None = None
    testcase_id: str | None = None
    project_id: str | None = None
    type_id: str | None = None
    severity: str | None = None
    environment: str | None = None
    estimated_hours: float | None = None
    spent_hours: float | None = None
    parent_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee: str | None = None
    assignee_id: str | None = None
    labels: list[str] | None = None
    due_date: datetime | None = None
    type_id: str | None = None
    status_id: str | None = None
    severity: str | None = None
    environment: str | None = None
    estimated_hours: float | None = None
    spent_hours: float | None = None
    parent_id: str | None = None


class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: str


@router.get("")
async def list_tasks(
    q: str | None = Query(default=None, description="Search query"),
    jql: str | None = Query(default=None, description="JQL filter"),
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    assignee_id: str | None = None,
    type_id: str | None = None,
    severity: str | None = None,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List tasks with filters. Supports JQL queries."""
    service = TaskService(db)

    if jql:
        try:
            compiler = JQLCompiler()
            ctx = JQLContext(
                current_user_id=user.id,
                project_id=project_id,
                db=db,
            )
            result = await compiler.compile(jql, ctx)
            return await service.list_tasks_jql(
                where_clause=result.where_clause,
                order_clauses=result.order_clauses,
                project_id=project_id,
            )
        except JQLSyntaxError as e:
            raise HTTPException(status_code=400, detail={
                "error": "jql_syntax_error",
                "message": e.message,
                "position": e.position,
                "jql": jql,
            })
        except JQLError as e:
            raise HTTPException(status_code=400, detail={
                "error": "jql_error",
                "message": str(e),
                "jql": jql,
            })

    if q:
        return await service.search_tasks(q, limit=20)
    return await service.list_tasks(
        status=status,
        priority=priority,
        assignee=assignee,
        assignee_id=assignee_id,
        type_id=type_id,
        severity=severity,
        project_id=project_id,
    )


@router.get("/board")
async def get_board(
    project_id: str | None = None,
    type_slug: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get tasks grouped by status for Kanban board."""
    service = TaskService(db)
    return await service.get_board(project_id=project_id, type_slug=type_slug)


@router.get("/board/{type_slug}")
async def get_board_by_type(
    type_slug: str,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Kanban board for specific task type."""
    service = TaskService(db)
    return await service.get_board(project_id=project_id, type_slug=type_slug)


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get task counts by status."""
    service = TaskService(db)
    return await service.get_stats()


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get task by ID."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return service.to_detail_dict(task)


@router.get("/{task_id}/children")
async def get_children(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get direct child tasks."""
    service = TaskService(db)
    return await service.get_children(task_id)


@router.post("")
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new task."""
    service = TaskService(db)
    try:
        task = await service.create_task(
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            assignee=data.assignee,
            assignee_id=data.assignee_id,
            reporter_id=user.id,
            labels=data.labels,
            due_date=data.due_date,
            session_id=data.session_id,
            testcase_id=data.testcase_id,
            project_id=data.project_id,
            type_id=data.type_id,
            severity=data.severity,
            environment=data.environment,
            estimated_hours=data.estimated_hours,
            spent_hours=data.spent_hours,
            parent_id=data.parent_id,
        )
    except TaskDepthExceededError:
        raise HTTPException(status_code=400, detail="Maximum task depth exceeded")
    return {"id": task.id, "human_id": task.human_id, "message": "Task created"}


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update task."""
    service = TaskService(db)
    task = await service.update_task(task_id, actor_id=user.id, **data.model_dump(exclude_unset=True))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task updated"}


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete task."""
    service = TaskService(db)
    deleted = await service.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}


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

    # Parse before timestamp
    before_dt = None
    if before:
        try:
            before_dt = dt.fromisoformat(before)
        except ValueError:
            pass

    # Query comments
    comments_q = (
        select(
            TaskComment.id,
            TaskComment.created_at,
            literal_column("'comment'").label("entry_type"),
        )
        .where(TaskComment.task_id == task_id)
    )
    if before_dt:
        comments_q = comments_q.where(TaskComment.created_at < before_dt)

    # Query activities
    activities_q = (
        select(
            TaskActivity.id,
            TaskActivity.created_at,
            literal_column("'activity'").label("entry_type"),
        )
        .where(TaskActivity.task_id == task_id)
    )
    if before_dt:
        activities_q = activities_q.where(TaskActivity.created_at < before_dt)

    # Combine and sort
    combined = union_all(comments_q, activities_q).subquery()
    final_q = (
        select(combined.c.id, combined.c.entry_type)
        .order_by(combined.c.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(final_q)
    entries = result.all()

    # Split IDs by type
    comment_ids = [eid for eid, etype in entries if etype == "comment"]
    activity_ids = [eid for eid, etype in entries if etype == "activity"]

    # Batch fetch with joinedload (2 queries instead of N)
    comments_map = {}
    if comment_ids:
        res = await db.execute(
            select(TaskComment)
            .options(joinedload(TaskComment.author))
            .where(TaskComment.id.in_(comment_ids))
        )
        comments_map = {c.id: c for c in res.unique().scalars()}

    activities_map = {}
    if activity_ids:
        res = await db.execute(
            select(TaskActivity)
            .options(joinedload(TaskActivity.actor))
            .where(TaskActivity.id.in_(activity_ids))
        )
        activities_map = {a.id: a for a in res.unique().scalars()}

    # Build feed preserving UNION ALL order
    feed = []
    for entry_id, entry_type in entries:
        if entry_type == "comment":
            comment = comments_map.get(entry_id)
            if comment:
                feed.append({
                    "entry_type": "comment",
                    "id": comment.id,
                    "content": comment.content,
                    "is_edited": comment.is_edited,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
                    "author": {
                        "id": comment.author.id,
                        "username": comment.author.username,
                        "display_name": comment.author.display_name,
                    } if comment.author else None,
                })
        else:
            activity = activities_map.get(entry_id)
            if activity:
                feed.append({
                    "entry_type": "activity",
                    "id": activity.id,
                    "action_type": activity.action_type,
                    "field_name": activity.field_name,
                    "old_value": activity.old_value,
                    "new_value": activity.new_value,
                    "created_at": activity.created_at.isoformat(),
                    "actor": {
                        "id": activity.actor.id,
                        "username": activity.actor.username,
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

    comment = TaskComment(
        task_id=task_id,
        author_id=user.id,
        content=data.content,
    )
    db.add(comment)

    # Record activity
    await service._record_activity(
        task_id, user.id, "commented",
        new_value={"comment_id": comment.id},
    )

    await db.commit()
    await db.refresh(comment)

    return {
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "author": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
        },
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
        select(TaskComment).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
        )
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
        select(TaskComment).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task_id,
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to delete this comment")

    await db.execute(delete(TaskComment).where(TaskComment.id == comment_id))
    await db.commit()

    return {"message": "Comment deleted"}


# ---- Relations ----

@router.get("/{task_id}/relations")
async def get_relations(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get all relations for a task."""
    from app.services.task_relation_service import TaskRelationService
    service = TaskRelationService(db)
    return await service.get_relations(task_id)


@router.post("/{task_id}/relations")
async def create_relation(
    task_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a relation between tasks."""
    from app.services.task_relation_service import TaskRelationService
    service = TaskRelationService(db)
    target_task_id = data.get("target_task_id")
    relation_type = data.get("relation_type")
    if not target_task_id or not relation_type:
        raise HTTPException(status_code=400, detail="target_task_id and relation_type are required")
    relation = await service.create_relation(task_id, target_task_id, relation_type, user.id)
    await db.commit()
    return {"id": relation.id, "message": "Relation created"}


@router.delete("/{task_id}/relations/{relation_id}")
async def delete_relation(
    task_id: str,
    relation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete a relation (both directions)."""
    from app.services.task_relation_service import TaskRelationService
    service = TaskRelationService(db)
    deleted = await service.delete_relation(relation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relation not found")
    await db.commit()
    return {"message": "Relation deleted"}
