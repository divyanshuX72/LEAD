"""
Base Repository

Generic repository providing CRUD operations for all entities.
Follows the Repository Pattern — no SQL in services or controllers.
"""

from typing import TypeVar, Generic, Type, Sequence
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from platform_app.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic async repository with common CRUD operations."""

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> T:
        """Create a new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, entity_id: str) -> T | None:
        """Get entity by ID."""
        stmt = select(self.model).where(self.model.id == entity_id)
        # Apply soft-delete filter if model supports it
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
        order_by: str | None = None,
    ) -> Sequence[T]:
        """Get all entities with optional filtering and pagination."""
        stmt = select(self.model)

        # Apply soft-delete filter
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted == False)  # noqa: E712

        # Apply filters
        if filters:
            conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)
            if conditions:
                stmt = stmt.where(and_(*conditions))

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            stmt = stmt.order_by(getattr(self.model, order_by).desc())
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, entity_id: str, **kwargs) -> T | None:
        """Update an entity by ID."""
        instance = await self.get_by_id(entity_id)
        if not instance:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key) and key != "id":
                setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, entity_id: str, soft: bool = True) -> bool:
        """Delete an entity. Soft-delete by default."""
        instance = await self.get_by_id(entity_id)
        if not instance:
            return False
        if soft and hasattr(instance, "is_deleted"):
            from datetime import datetime
            instance.is_deleted = True  # type: ignore
            instance.deleted_at = datetime.utcnow()  # type: ignore
        else:
            await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self, filters: dict | None = None) -> int:
        """Count entities with optional filters."""
        stmt = select(func.count()).select_from(self.model)
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted == False)  # noqa: E712
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, **kwargs) -> bool:
        """Check if an entity exists with given criteria."""
        stmt = select(func.count()).select_from(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
