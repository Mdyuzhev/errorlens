"""Task relations router — split from tasks.py (EL031)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


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
