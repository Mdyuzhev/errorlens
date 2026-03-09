"""Task relation service — blocks, duplicates, relates_to."""

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Task, TaskRelation

# Symmetric inverse mapping
INVERSE_TYPES = {
    "blocks": "blocked_by",
    "blocked_by": "blocks",
    "duplicates": "duplicated_by",
    "duplicated_by": "duplicates",
    "relates_to": "relates_to",
}

VALID_RELATION_TYPES = set(INVERSE_TYPES.keys())


class TaskRelationService:
    """Business logic for task relations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_relation(
        self, source_task_id: str, target_task_id: str,
        relation_type: str, created_by: str | None = None,
    ) -> TaskRelation:
        if relation_type not in VALID_RELATION_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid relation type: {relation_type}")

        if source_task_id == target_task_id:
            raise HTTPException(status_code=400, detail="Cannot relate task to itself")

        # Check duplicate
        existing = await self.db.execute(
            select(TaskRelation).where(
                TaskRelation.source_task_id == source_task_id,
                TaskRelation.target_task_id == target_task_id,
                TaskRelation.relation_type == relation_type,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Relation already exists")

        # Check cyclic blocks
        if relation_type in ("blocks", "blocked_by"):
            await self._validate_no_cycle(source_task_id, target_task_id, relation_type)

        # Create forward relation
        forward = TaskRelation(
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            relation_type=relation_type,
            created_by=created_by,
        )
        self.db.add(forward)

        # Create inverse relation
        inverse_type = INVERSE_TYPES[relation_type]
        inverse = TaskRelation(
            source_task_id=target_task_id,
            target_task_id=source_task_id,
            relation_type=inverse_type,
            created_by=created_by,
        )
        self.db.add(inverse)

        await self.db.flush()
        return forward

    async def delete_relation(self, relation_id: str) -> bool:
        result = await self.db.execute(
            select(TaskRelation).where(TaskRelation.id == relation_id)
        )
        relation = result.scalar_one_or_none()
        if not relation:
            return False

        # Delete both forward and inverse
        inverse_type = INVERSE_TYPES.get(relation.relation_type, relation.relation_type)
        await self.db.execute(
            delete(TaskRelation).where(
                TaskRelation.source_task_id == relation.target_task_id,
                TaskRelation.target_task_id == relation.source_task_id,
                TaskRelation.relation_type == inverse_type,
            )
        )
        await self.db.execute(
            delete(TaskRelation).where(TaskRelation.id == relation_id)
        )
        await self.db.flush()
        return True

    async def get_relations(self, task_id: str) -> list[dict]:
        result = await self.db.execute(
            select(TaskRelation).where(TaskRelation.source_task_id == task_id)
        )
        relations = list(result.scalars().all())

        output = []
        for r in relations:
            # Load target task info
            task_result = await self.db.execute(
                select(Task).where(Task.id == r.target_task_id)
            )
            target = task_result.scalar_one_or_none()
            output.append({
                "id": r.id,
                "relation_type": r.relation_type,
                "target_task_id": r.target_task_id,
                "target_task": {
                    "id": target.id,
                    "human_id": target.human_id,
                    "title": target.title,
                    "status": target.status,
                } if target else None,
                "created_at": r.created_at.isoformat(),
            })
        return output

    async def _validate_no_cycle(
        self, source_id: str, target_id: str, relation_type: str
    ) -> None:
        """Check that adding this relation doesn't create a cycle in blocks graph."""
        # If A blocks B, check B doesn't already block A (directly or transitively)
        if relation_type == "blocks":
            blocker_id, blocked_id = source_id, target_id
        else:
            blocker_id, blocked_id = target_id, source_id

        # BFS: follow "blocks" edges from blocked_id to see if we reach blocker_id
        visited = set()
        queue = [blocked_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            result = await self.db.execute(
                select(TaskRelation.target_task_id).where(
                    TaskRelation.source_task_id == current,
                    TaskRelation.relation_type == "blocks",
                )
            )
            for (next_id,) in result.all():
                if next_id == blocker_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Cyclic blocking dependency detected",
                    )
                queue.append(next_id)
