"""Test cases CRUD router."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.db_models import TestCase
from app.models.user import User

router = APIRouter(prefix="/testcases", tags=["testcases"])


class TestCaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    postconditions: Optional[str] = None
    priority: str = "Medium"
    status: str = "Draft"
    automation_status: str = "Manual"
    folder: Optional[str] = None
    tags: list[str] = []
    steps: list[dict] = []
    session_id: Optional[str] = None


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    preconditions: Optional[str] = None
    postconditions: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    automation_status: Optional[str] = None
    folder: Optional[str] = None
    tags: Optional[list[str]] = None
    steps: Optional[list[dict]] = None


@router.get("")
async def list_testcases(
    folder: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List test cases with filters."""
    query = select(TestCase).order_by(TestCase.created_at.desc())

    if folder:
        query = query.where(TestCase.folder == folder)
    if status:
        query = query.where(TestCase.status == status)
    if priority:
        query = query.where(TestCase.priority == priority)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    testcases = result.scalars().all()

    return [
        {
            "id": tc.id,
            "title": tc.title,
            "description": tc.description,
            "preconditions": tc.preconditions,
            "postconditions": tc.postconditions,
            "priority": tc.priority,
            "status": tc.status,
            "automation_status": tc.automation_status,
            "folder": tc.folder,
            "tags": tc.tags,
            "steps": tc.steps,
            "created_at": tc.created_at.isoformat() if tc.created_at else None,
            "created_by": tc.created_by,
        }
        for tc in testcases
    ]


@router.get("/folders/list")
async def list_folders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get unique folders."""
    result = await db.execute(
        select(TestCase.folder).distinct().where(TestCase.folder.isnot(None))
    )
    folders = [r[0] for r in result.all() if r[0]]
    return folders


@router.get("/{testcase_id}")
async def get_testcase(
    testcase_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test case by ID."""
    result = await db.execute(select(TestCase).where(TestCase.id == testcase_id))
    tc = result.scalar_one_or_none()

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    return {
        "id": tc.id,
        "title": tc.title,
        "description": tc.description,
        "preconditions": tc.preconditions,
        "postconditions": tc.postconditions,
        "priority": tc.priority,
        "status": tc.status,
        "automation_status": tc.automation_status,
        "folder": tc.folder,
        "tags": tc.tags,
        "steps": tc.steps,
        "created_at": tc.created_at.isoformat() if tc.created_at else None,
        "created_by": tc.created_by,
        "session_id": tc.session_id,
    }


@router.post("")
async def create_testcase(
    data: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new test case."""
    tc = TestCase(
        title=data.title,
        description=data.description,
        preconditions=data.preconditions,
        postconditions=data.postconditions,
        priority=data.priority,
        status=data.status,
        automation_status=data.automation_status,
        folder=data.folder,
        tags=data.tags,
        steps=data.steps,
        session_id=data.session_id,
        created_by=user.username,
    )

    db.add(tc)
    await db.commit()
    await db.refresh(tc)

    return {"id": tc.id, "message": "Test case created"}


@router.put("/{testcase_id}")
async def update_testcase(
    testcase_id: str,
    data: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update test case."""
    result = await db.execute(select(TestCase).where(TestCase.id == testcase_id))
    tc = result.scalar_one_or_none()

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tc, key, value)

    tc.updated_at = datetime.utcnow()
    await db.commit()

    return {"message": "Test case updated"}


@router.delete("/{testcase_id}")
async def delete_testcase(
    testcase_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete test case."""
    result = await db.execute(select(TestCase).where(TestCase.id == testcase_id))
    tc = result.scalar_one_or_none()

    if not tc:
        raise HTTPException(status_code=404, detail="Test case not found")

    await db.delete(tc)
    await db.commit()

    return {"message": "Test case deleted"}
