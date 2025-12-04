"""
User Repository for user data access.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.user import User
from app.models.db_models import ProjectMember


class UserRepository(BaseRepository[User]):
    """Repository for User model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return await self.get_by_field("email", email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.get_by_field("username", username)

    async def get_by_email_or_username(
        self,
        identifier: str
    ) -> Optional[User]:
        """Get user by either email or username."""
        query = select(User).where(
            or_(User.email == identifier, User.username == identifier)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_with_projects(self, user_id: str) -> Optional[User]:
        """Get user with their project memberships."""
        query = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.owned_projects),
                selectinload(User.project_memberships).selectinload(ProjectMember.project),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get all active users."""
        query = (
            select(User)
            .where(User.is_active == True)  # noqa: E712
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        display_name: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        return await self.create({
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "display_name": display_name or username,
            "is_active": True,
        })

    async def update_password(
        self,
        user_id: str,
        hashed_password: str
    ) -> Optional[User]:
        """Update user password."""
        return await self.update(user_id, {"hashed_password": hashed_password})

    async def deactivate(self, user_id: str) -> Optional[User]:
        """Deactivate user account."""
        return await self.update(user_id, {"is_active": False})

    async def activate(self, user_id: str) -> Optional[User]:
        """Activate user account."""
        return await self.update(user_id, {"is_active": True})

    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        user = await self.get_by_email(email)
        return user is not None

    async def username_exists(self, username: str) -> bool:
        """Check if username is already taken."""
        user = await self.get_by_username(username)
        return user is not None
