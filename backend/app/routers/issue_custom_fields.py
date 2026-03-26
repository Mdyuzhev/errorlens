"""Issue custom fields router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import IssueCustomField, IssueCustomValue
from app.models.user import User

router = APIRouter(prefix="/api/v1/custom-fields", tags=["custom-fields"])


class CustomFieldCreate(BaseModel):
    project_id: str
    task_type_id: str | None = None
    name: str
    field_type: str
    options: dict | None = None
    is_required: bool = False


class CustomFieldUpdate(BaseModel):
    name: str | None = None
    options: dict | None = None
    is_required: bool | None = None
    sort_order: int | None = None


class CustomValueSet(BaseModel):
    field_id: str
    value: dict | None = None


@router.get("")
async def list_fields(
    project_id: str = Query(...),
    task_type_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List custom field definitions."""
    q = select(IssueCustomField).where(IssueCustomField.project_id == project_id)
    if task_type_id:
        q = q.where(IssueCustomField.task_type_id == task_type_id)
    q = q.order_by(IssueCustomField.sort_order)
    result = await db.execute(q)
    return [
        {
            "id": f.id, "name": f.name, "field_type": f.field_type,
            "options": f.options, "is_required": f.is_required,
            "task_type_id": f.task_type_id, "sort_order": f.sort_order,
        }
        for f in result.scalars().all()
    ]


@router.post("")
async def create_field(
    data: CustomFieldCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a custom field."""
    field = IssueCustomField(
        project_id=data.project_id, task_type_id=data.task_type_id,
        name=data.name, field_type=data.field_type,
        options=data.options, is_required=data.is_required,
    )
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return {"id": field.id, "message": "Custom field created"}


@router.put("/{field_id}")
async def update_field(
    field_id: str,
    data: CustomFieldUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update custom field."""
    field = await db.get(IssueCustomField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(field, k, v)
    await db.commit()
    return {"message": "Custom field updated"}


@router.delete("/{field_id}")
async def delete_field(
    field_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete custom field and its values."""
    from sqlalchemy import delete

    field = await db.get(IssueCustomField, field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Custom field not found")
    await db.execute(delete(IssueCustomValue).where(IssueCustomValue.field_id == field_id))
    await db.delete(field)
    await db.commit()
    return {"message": "Custom field deleted"}


@router.put("/issues/{issue_id}/values")
async def set_values(
    issue_id: str,
    data: list[CustomValueSet],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Set custom field values for an issue."""
    for item in data:
        existing = await db.execute(
            select(IssueCustomValue).where(
                IssueCustomValue.issue_id == issue_id,
                IssueCustomValue.field_id == item.field_id,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.value = item.value
        else:
            db.add(IssueCustomValue(issue_id=issue_id, field_id=item.field_id, value=item.value))
    await db.commit()
    return {"message": "Values updated"}
