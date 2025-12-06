"""
Base Repository with generic CRUD operations.

Provides reusable data access patterns for SQLAlchemy models.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import Base

# Generic type for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with generic CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any, load_relations: list[str] | None = None) -> ModelType | None:
        """Get single record by ID."""
        query = select(self.model).where(self.model.id == id)

        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(self.model, relation)))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        load_relations: list[str] | None = None,
        order_by: Any | None = None,
    ) -> list[ModelType]:
        """Get all records with pagination."""
        query = select(self.model)

        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(self.model, relation)))

        if order_by is not None:
            query = query.order_by(order_by)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_field(
        self,
        field_name: str,
        value: Any,
        load_relations: list[str] | None = None,
    ) -> ModelType | None:
        """Get single record by field value."""
        field = getattr(self.model, field_name)
        query = select(self.model).where(field == value)

        if load_relations:
            for relation in load_relations:
                query = query.options(selectinload(getattr(self.model, relation)))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_many_by_field(
        self,
        field_name: str,
        value: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get multiple records by field value."""
        field = getattr(self.model, field_name)
        query = select(self.model).where(field == value).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Create new record."""
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: Any, data: dict[str, Any]) -> ModelType | None:
        """Update record by ID."""
        # Remove None values to avoid overwriting with nulls
        update_data = {k: v for k, v in data.items() if v is not None}

        if not update_data:
            return await self.get_by_id(id)

        stmt = update(self.model).where(self.model.id == id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.flush()

        return await self.get_by_id(id)

    async def delete(self, id: Any) -> bool:
        """Delete record by ID."""
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def count(self, **filters) -> int:
        """Count records with optional filters."""
        query = select(func.count()).select_from(self.model)

        for field_name, value in filters.items():
            field = getattr(self.model, field_name, None)
            if field is not None:
                query = query.where(field == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def exists(self, id: Any) -> bool:
        """Check if record exists."""
        query = select(func.count()).select_from(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[ModelType]:
        """Create multiple records at once."""
        instances = [self.model(**data) for data in items]
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Delete multiple records by IDs."""
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
