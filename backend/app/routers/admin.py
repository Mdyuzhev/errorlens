"""Admin endpoints for system management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
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
