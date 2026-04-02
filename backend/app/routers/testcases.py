"""Test cases CRUD router - thin controller."""

import csv
import io
import json as json_lib
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.providers.factory import ProviderFactory
from app.services.testcase_service import TestCaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/testcases", tags=["testcases"])


class TestCaseCreate(BaseModel):
    title: str
    description: str | None = None
    preconditions: str | None = None
    postconditions: str | None = None
    priority: str = "Medium"
    status: str = "Draft"
    automation_status: str = "Manual"
    folder: str | None = None
    folder_id: str | None = None
    tags: list[str] = []
    steps: list[dict] = []
    session_id: str | None = None
    project_id: str | None = None


class ImproveRequest(BaseModel):
    provider: str = "ollama"
    model: str = "mistral"
    api_key: str | None = None


class ImprovedStep(BaseModel):
    action: str
    expected: str
    data: str | None = None


class ImproveResponse(BaseModel):
    title: str
    description: str | None = None
    preconditions: str | None = None
    postconditions: str | None = None
    steps: list[ImprovedStep] = []


class TestCaseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    preconditions: str | None = None
    postconditions: str | None = None
    priority: str | None = None
    status: str | None = None
    automation_status: str | None = None
    folder: str | None = None
    tags: list[str] | None = None
    steps: list[dict] | None = None
    parameters: list[dict] | None = None
    linked_issue_ids: list[str] | None = None
    linked_article_ids: list[str] | None = None


@router.get("")
async def list_testcases(
    q: str | None = Query(default=None, description="Search query"),
    folder: str | None = None,
    folder_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    linked_issue_id: str | None = None,
    project_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List test cases with pagination."""
    service = TestCaseService(db)

    if q and not linked_issue_id:
        items = await service.search_testcases(q, project_id=project_id, limit=limit, offset=offset)
        total = await service.count_testcases(folder_id=folder_id, q=q, project_id=project_id)
    else:
        items = await service.list_testcases(
            folder=folder,
            folder_id=folder_id,
            status=status,
            priority=priority,
            linked_issue_id=linked_issue_id,
            project_id=project_id,
            limit=limit,
            offset=offset,
        )
        total = await service.count_testcases(
            folder_id=folder_id,
            folder=folder,
            status=status,
            priority=priority,
            project_id=project_id,
        )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/search")
async def search_testcases(
    q: str = Query(..., min_length=1),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Search test cases by title or description."""
    service = TestCaseService(db)
    return await service.search_testcases(q, limit=limit, offset=offset)


@router.get("/by-tags")
async def get_by_tags(
    tags: list[str] = Query(...),
    match_all: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test cases by tags."""
    service = TestCaseService(db)
    return await service.get_by_tags(tags, match_all=match_all)


@router.get("/folders/list")
async def list_folders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get unique folders."""
    service = TestCaseService(db)
    return await service.get_folders()


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test case statistics."""
    service = TestCaseService(db)
    return await service.get_stats()


@router.get("/export/csv")
async def export_testcases_csv(
    project_id: str = Query(...),
    folder_id: str | None = Query(default=None),
    ids: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Export test cases as CSV."""
    service = TestCaseService(db)
    cases = await service.list_testcases(folder_id=folder_id, limit=5000, offset=0)
    if ids:
        cases = [c for c in cases if c.id in ids]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["human_id", "title", "priority", "status",
                     "automation_status", "tags", "steps", "preconditions", "postconditions"])
    for c in cases:
        writer.writerow([
            c.human_id or "", c.title, c.priority, c.status,
            c.automation_status, ",".join(c.tags or []),
            str(c.steps or []), c.preconditions or "", c.postconditions or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=testcases.csv"},
    )


@router.get("/{testcase_id}")
async def get_testcase(
    testcase_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test case by ID."""
    service = TestCaseService(db)
    tc = await service.get_testcase(testcase_id)

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    return service.to_detail_dict(tc)


@router.post("")
async def create_testcase(
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new test case."""
    service = TestCaseService(db)
    tc = await service.create_testcase(
        title=data.title,
        created_by=user.username,
        description=data.description,
        preconditions=data.preconditions,
        postconditions=data.postconditions,
        priority=data.priority,
        status=data.status,
        automation_status=data.automation_status,
        folder=data.folder,
        folder_id=data.folder_id,
        tags=data.tags,
        steps=data.steps,
        session_id=data.session_id,
        project_id=data.project_id,
    )
    return {"id": tc.id, "message": "Test case created"}


@router.put("/{testcase_id}")
async def update_testcase(
    testcase_id: str,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update test case."""
    service = TestCaseService(db)
    tc = await service.update_testcase(testcase_id, **data.model_dump(exclude_unset=True))

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    return {"message": "Test case updated"}


@router.patch("/{testcase_id}/status")
async def update_status(
    testcase_id: str,
    status: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update test case status."""
    service = TestCaseService(db)
    tc = await service.update_status(testcase_id, status)

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found or invalid status")

    return {"message": f"Status updated to {status}"}


@router.patch("/{testcase_id}/automation")
async def update_automation_status(
    testcase_id: str,
    automation_status: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update automation status."""
    service = TestCaseService(db)
    tc = await service.update_automation_status(testcase_id, automation_status)

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found or invalid status")

    return {"message": f"Automation status updated to {automation_status}"}


@router.delete("/{testcase_id}")
async def delete_testcase(
    testcase_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete test case."""
    service = TestCaseService(db)
    deleted = await service.delete_testcase(testcase_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Test case not found")

    return {"message": "Test case deleted"}


@router.post("/{testcase_id}/improve", response_model=ImproveResponse)
async def improve_testcase(
    testcase_id: str,
    data: ImproveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Improve test case using LLM."""
    service = TestCaseService(db)
    tc = await service.get_testcase(testcase_id)

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    steps_text = ""
    if tc.steps:
        for i, step in enumerate(tc.steps, 1):
            action = step.get("action", "")
            expected = step.get("expected", "")
            steps_text += f"  {i}. Action: {action} | Expected: {expected}\n"

    prompt = (
        "Ты опытный QA-инженер. Улучши следующий тест-кейс: "
        "сделай шаги конкретнее, добавь недостающие проверки, улучши ожидаемые результаты, "
        "дополни предусловия и постусловия. Отвечай ТОЛЬКО на русском языке.\n\n"
        f"Название: {tc.title}\n"
        f"Описание: {tc.description or 'Нет'}\n"
        f"Предусловия: {tc.preconditions or 'Нет'}\n"
        f"Постусловия: {tc.postconditions or 'Нет'}\n"
        f"Шаги:\n{steps_text or '  Нет'}\n\n"
        "Верни ТОЛЬКО валидный JSON (без markdown), строго такой структуры:\n"
        '{"title": "...", "description": "...", "preconditions": "...", '
        '"postconditions": "...", "steps": [{"action": "...", "expected": "...", "data": "..."}]}'
    )

    provider = ProviderFactory.create(
        data.provider,
        api_key=data.api_key or None,
        model=data.model or None,
    )
    try:
        raw = await provider.generate(prompt, max_tokens=2048)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    logger.info("LLM improve raw response (first 500 chars): %s", raw[:500])

    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    try:
        result = json_lib.loads(cleaned)
    except json_lib.JSONDecodeError:
        # Try to fix common LLM JSON issues: trailing commas, unescaped quotes
        fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)  # trailing commas
        fixed = re.sub(r'""([^"]+)""', r'"\1"', fixed)  # double-double quotes
        try:
            result = json_lib.loads(fixed)
        except json_lib.JSONDecodeError:
            # Last resort: extract first { ... } block
            m = re.search(r'\{[\s\S]*\}', fixed)
            if m:
                try:
                    result = json_lib.loads(m.group())
                except json_lib.JSONDecodeError:
                    raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
            else:
                raise HTTPException(status_code=502, detail="LLM returned invalid JSON")

    def _str(val: object) -> str | None:
        if val is None:
            return None
        return val if isinstance(val, str) else json_lib.dumps(val, ensure_ascii=False)

    steps = []
    for s in result.get("steps", []):
        steps.append(ImprovedStep(
            action=_str(s.get("action", "")) or "",
            expected=_str(s.get("expected", "")) or "",
            data=_str(s.get("data")),
        ))

    return ImproveResponse(
        title=_str(result.get("title", tc.title)) or tc.title,
        description=_str(result.get("description")),
        preconditions=_str(result.get("preconditions")),
        postconditions=_str(result.get("postconditions")),
        steps=steps,
    )
