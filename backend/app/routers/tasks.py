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
    component_id: str | None = None
    story_points: int | None = None
    sprint_id: str | None = None


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
    component_id: str | None = None
    story_points: int | None = None


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


@router.get("/backlog")
async def get_backlog(
    project_id: str | None = Query(default=None),
    component_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Issues without sprint assignment, sorted by rank."""
    from sqlalchemy import select
    from app.models.task import SprintIssue, Task
    subq = select(SprintIssue.issue_id)
    q = select(Task).where(Task.id.not_in(subq))
    if project_id:
        q = q.where(Task.project_id == project_id)
    if component_id:
        q = q.where(Task.component_id == component_id)
    q = q.order_by(Task.rank.asc())
    result = await db.execute(q)
    tasks = result.scalars().all()
    service = TaskService(db)
    return [service._to_list_dict(t) for t in tasks]


@router.patch("/{task_id}/rank")
async def update_task_rank(
    task_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update task rank and optionally move to sprint."""
    from sqlalchemy import delete
    from app.models.task import SprintIssue, Task
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.rank = data.get("rank", 0)
    if data.get("sprint_id"):
        await db.execute(delete(SprintIssue).where(SprintIssue.issue_id == task_id))
        db.add(SprintIssue(sprint_id=data["sprint_id"], issue_id=task_id, rank=task.rank))
    await db.commit()
    return {"message": "Rank updated"}


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Aggregated issue stats with Redis cache."""
    from fastapi.responses import JSONResponse
    from app.services.dashboard_service import DashboardService
    svc = DashboardService(db)
    data, hit = await svc.get_stats(project_id)
    resp = JSONResponse(content=data)
    resp.headers["X-Cache"] = "HIT" if hit else "MISS"
    return resp


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
    detail = service.to_detail_dict(task)
    from app.repositories.attachment_repo import IssueAttachmentRepository
    from app.repositories.work_log_repo import WorkLogRepository
    from app.repositories.custom_field_repo import IssueCustomValueRepository
    detail["attachments"] = [
        {"id": a.id, "filename": a.filename, "size_bytes": a.size_bytes,
         "content_type": a.content_type, "created_at": a.created_at.isoformat()}
        for a in await IssueAttachmentRepository(db).list_by_issue(task_id)
    ]
    detail["work_logs"] = [
        {"id": w.id, "hours": w.hours, "log_date": w.log_date.isoformat(),
         "comment": w.comment, "user_id": w.user_id}
        for w in await WorkLogRepository(db).list_by_issue(task_id)
    ]
    detail["custom_field_values"] = await IssueCustomValueRepository(db).get_values_for_issue(task_id)
    detail["story_points"] = task.story_points
    detail["component_id"] = task.component_id
    return detail


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
    # Set component_id and story_points directly on the task object
    if data.component_id or data.story_points is not None:
        if data.component_id:
            task.component_id = data.component_id
        if data.story_points is not None:
            task.story_points = data.story_points
        await db.commit()
    if data.sprint_id:
        from app.models.task import SprintIssue
        si = SprintIssue(sprint_id=data.sprint_id, issue_id=task.id, rank=0)
        db.add(si)
        await db.commit()
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
