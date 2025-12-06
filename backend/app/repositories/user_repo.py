"""
User Repository for user data access.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import ProjectMember
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        return await self.get_by_field("email", email)

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        return await self.get_by_field("username", username)

    async def get_by_email_or_username(self, identifier: str) -> User | None:
        """Get user by either email or username."""
        query = select(User).where(or_(User.email == identifier, User.username == identifier))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_with_projects(self, user_id: str) -> User | None:
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

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users."""
        query = select(User).where(User.is_active == True).offset(skip).limit(limit)  # noqa: E712
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        display_name: str | None = None,
    ) -> User:
        """Create a new user."""
        return await self.create(
            {
                "username": username,
                "email": email,
                "hashed_password": hashed_password,
                "display_name": display_name or username,
                "is_active": True,
            }
        )

    async def update_password(self, user_id: str, hashed_password: str) -> User | None:
        """Update user password."""
        return await self.update(user_id, {"hashed_password": hashed_password})

    async def deactivate(self, user_id: str) -> User | None:
        """Deactivate user account."""
        return await self.update(user_id, {"is_active": False})

    async def activate(self, user_id: str) -> User | None:
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
