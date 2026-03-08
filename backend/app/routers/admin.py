"""Admin endpoints for system management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.auth import create_user, get_password_hash
from app.services.seed_test_users import clear_test_users, seed_test_users

router = APIRouter(prefix="/admin", tags=["Admin"])


class SeedResult(BaseModel):
    """Result of seeding operation."""

    users_created: list[str]
    users_skipped: list[str]
    projects_created: list[str]
    projects_skipped: list[str]
    memberships_created: list[str]


class ClearResult(BaseModel):
    """Result of clearing operation."""

    users_deleted: int
    projects_deleted: int


def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin user for endpoint access."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/seed-test-users", response_model=SeedResult)
async def seed_test_users_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> SeedResult:
    """
    Seed test users and projects for smoke testing.

    Creates 6 test users with predefined roles:
    - owner1, owner2: Project owners
    - admin1: Project admin
    - member1: Project member
    - viewer1, viewer2: Project viewers

    All users have password: Test123!
    """
    result = await seed_test_users(db)
    return SeedResult(**result)


@router.delete("/seed-test-users", response_model=ClearResult)
async def clear_test_users_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> ClearResult:
    """
    Remove all test users and their projects.

    Useful for cleanup after smoke testing.
    """
    result = await clear_test_users(db)
    return ClearResult(**result)


# --- Schemas for user management ---


class AdminUserCreate(BaseModel):
    """Create user request."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    is_admin: bool = False


class AdminPasswordChange(BaseModel):
    """Change password request."""

    new_password: str = Field(min_length=6)


class AdminToggleActive(BaseModel):
    """Toggle active status request."""

    is_active: bool


class AdminUserResponse(BaseModel):
    """User info for admin panel."""

    id: str
    username: str
    is_admin: bool
    is_active: bool
    created_at: datetime | None = None
    last_login: datetime | None = None

    class Config:
        from_attributes = True


# --- User management endpoints ---


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> list[AdminUserResponse]:
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return [AdminUserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user_endpoint(
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> AdminUserResponse:
    """Create a new user."""
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = await create_user(db, data.username, data.password, data.is_admin)
    return AdminUserResponse.model_validate(new_user)


@router.patch("/users/{user_id}/password")
async def change_user_password(
    user_id: str,
    data: AdminPasswordChange,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Change user password."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.hashed_password = get_password_hash(data.new_password)
    await db.commit()
    return {"message": "Password changed"}


@router.patch("/users/{user_id}/active", response_model=AdminUserResponse)
async def toggle_user_active(
    user_id: str,
    data: AdminToggleActive,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdminUserResponse:
    """Toggle user active status."""
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_active = data.is_active
    await db.commit()
    await db.refresh(target_user)
    return AdminUserResponse.model_validate(target_user)
