"""Custom Fields API router — CRUD for field definitions and task values."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import check_project_access, require_auth
from app.models.user import User
from app.repositories.custom_field_repo import (
    IssueCustomFieldRepository,
    IssueCustomValueRepository,
)

router = APIRouter(prefix="/v1/custom-fields", tags=["custom-fields"])


# ── Schemas ──────────────────────────────────────────────


class CreateFieldRequest(BaseModel):
    project_id: str
    task_type_id: str | None = None
    name: str
    field_type: str
    options: dict | None = None
    sort_order: int = 0
    is_required: bool = False


class UpdateFieldRequest(BaseModel):
    name: str | None = None
    field_type: str | None = None
    options: dict | None = None
    sort_order: int | None = None
    is_required: bool | None = None


class SetValuesRequest(BaseModel):
    values: dict[str, object]


# ── Helpers ──────────────────────────────────────────────


def _field_to_dict(field) -> dict:
    return {
        "id": field.id,
        "project_id": field.project_id,
        "task_type_id": field.task_type_id,
        "name": field.name,
        "field_type": field.field_type,
        "options": field.options,
        "sort_order": field.sort_order,
        "is_required": field.is_required,
    }


# ── Field CRUD ───────────────────────────────────────────


@router.get("/")
async def list_fields(
    project_id: str,
    task_type_id: str | None = None,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List custom field definitions for a project."""
    await check_project_access(project_id, user, db)
    repo = IssueCustomFieldRepository(db)
    fields = await repo.list_by_project(project_id, task_type_id=task_type_id)
    return [_field_to_dict(f) for f in fields]


@router.post("/", status_code=201)
async def create_field(
    body: CreateFieldRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a custom field definition."""
    await check_project_access(body.project_id, user, db, required_role="admin")
    repo = IssueCustomFieldRepository(db)
    field = await repo.create(body.model_dump())
    await db.commit()
    return _field_to_dict(field)


@router.put("/{field_id}")
async def update_field(
    field_id: str,
    body: UpdateFieldRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a custom field definition."""
    repo = IssueCustomFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")

    await check_project_access(field.project_id, user, db, required_role="admin")

    data = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = await repo.update(field_id, data)
    await db.commit()
    return _field_to_dict(updated)


@router.delete("/{field_id}", status_code=204)
async def delete_field(
    field_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a custom field and cascade-delete its values."""
    repo = IssueCustomFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")

    await check_project_access(field.project_id, user, db, required_role="admin")

    # Values cascade-delete via FK ondelete=CASCADE
    await repo.delete(field_id)
    await db.commit()


# ── Values ───────────────────────────────────────────────


@router.get("/values/{issue_id}")
async def get_values(
    issue_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all custom field values for a task."""
    repo = IssueCustomValueRepository(db)
    values = await repo.get_values_for_issue(issue_id)
    return {"issue_id": issue_id, "values": values}


@router.put("/values/{issue_id}")
async def set_values(
    issue_id: str,
    body: SetValuesRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk set custom field values for a task."""
    repo = IssueCustomValueRepository(db)
    await repo.bulk_set_values(issue_id, body.values)
    await db.commit()
    values = await repo.get_values_for_issue(issue_id)
    return {"issue_id": issue_id, "values": values}
