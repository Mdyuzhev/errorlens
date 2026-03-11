"""JQL endpoints — validate, suggest, AI translate."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.jql import JQLCompiler, JQLError, JQLSyntaxError
from app.jql.fields import ALL_FIELD_NAMES, FIELD_REGISTRY
from app.middleware.jwt_auth import require_auth
from app.models.db_models import ProjectMember, TaskStatus, TaskType
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["jql"])


@router.get("/jql-validate")
async def jql_validate(
    jql: str = Query(..., description="JQL string to validate"),
    user: User = Depends(require_auth),
):
    """Validate JQL syntax without executing."""
    compiler = JQLCompiler()
    try:
        compiler.parse_only(jql)
        return {"valid": True}
    except JQLSyntaxError as e:
        return {"valid": False, "error": e.message, "position": e.position}
    except JQLError as e:
        return {"valid": False, "error": str(e)}


@router.get("/jql-suggest")
async def jql_suggest(
    field: str = Query(..., description="Field name for suggestions"),
    query: str = Query(default="", description="Search prefix"),
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get autocomplete suggestions for a JQL field value."""
    if not field:
        return [{"value": name} for name in sorted(ALL_FIELD_NAMES)]

    field_lower = field.lower()

    if field_lower == "priority":
        values = ["low", "medium", "high", "critical"]
        return [{"value": v} for v in values if query.lower() in v]

    if field_lower == "severity":
        values = ["trivial", "minor", "major", "critical"]
        return [{"value": v} for v in values if query.lower() in v]

    if field_lower == "environment":
        values = ["production", "staging", "local", "all"]
        return [{"value": v} for v in values if query.lower() in v]

    if field_lower in ("assignee", "reporter"):
        stmt = select(User.username, User.display_name)
        if project_id:
            stmt = stmt.join(ProjectMember, ProjectMember.user_id == User.id).where(
                ProjectMember.project_id == project_id
            )
        if query:
            stmt = stmt.where(User.username.ilike(f"%{query}%"))
        stmt = stmt.limit(20)
        result = await db.execute(stmt)
        return [
            {"value": row.username, "label": row.display_name or row.username}
            for row in result.all()
        ]

    if field_lower in ("status",):
        stmt = select(TaskStatus.slug, TaskStatus.name)
        if project_id:
            stmt = stmt.where(TaskStatus.project_id == project_id)
        if query:
            stmt = stmt.where(TaskStatus.slug.ilike(f"%{query}%"))
        result = await db.execute(stmt)
        return [{"value": row.slug, "label": row.name} for row in result.all()]

    if field_lower in ("type", "issuetype"):
        stmt = select(TaskType.slug, TaskType.name)
        if project_id:
            stmt = stmt.where(TaskType.project_id == project_id)
        if query:
            stmt = stmt.where(TaskType.slug.ilike(f"%{query}%"))
        result = await db.execute(stmt)
        return [{"value": row.slug, "label": row.name} for row in result.all()]

    if field_lower in ("label", "labels"):
        from sqlalchemy import distinct, func

        from app.models.db_models import Task

        stmt = select(distinct(func.jsonb_array_elements_text(Task.labels))).limit(50)
        if project_id:
            stmt = stmt.where(Task.project_id == project_id)
        try:
            result = await db.execute(stmt)
            labels = [row[0] for row in result.all()]
            if query:
                labels = [lbl for lbl in labels if query.lower() in lbl.lower()]
            return [{"value": lbl} for lbl in labels]
        except Exception:
            return []

    return []


@router.post("/jql-ai")
async def jql_ai(
    data: dict,
    user: User = Depends(require_auth),
):
    """Convert natural language query to JQL using Claude API."""
    import httpx

    from app.config import settings

    query_text = data.get("query", "")
    if not query_text:
        raise HTTPException(status_code=400, detail="query is required")

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    field_list = ", ".join(sorted(FIELD_REGISTRY.keys()))
    system_prompt = (
        "Ты конвертируешь запросы на естественном языке в JQL для системы "
        "управления задачами ErrorLens. "
        f"Доступные поля: {field_list}. "
        "Операторы: =, !=, <, >, <=, >=, in, not in, ~, !~, IS EMPTY, IS NOT EMPTY, WAS, CHANGED. "
        "Функции: currentUser(), now(), startOfDay(), endOfDay(), startOfWeek(), startOfMonth(). "
        "Верни только JQL-строку без объяснений."
    )

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 200,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": query_text}],
                },
            )
            resp.raise_for_status()
            result = resp.json()
            jql_text = result["content"][0]["text"].strip()
            return {"jql": jql_text}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"LLM API error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM API error: {str(e)}")
