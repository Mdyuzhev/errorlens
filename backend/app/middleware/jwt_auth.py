"""JWT authentication middleware."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Project, ProjectMember
from app.models.user import User
from app.services.auth import decode_token, get_user_by_id

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user from JWT token (optional - returns None if no token)."""
    if not credentials:
        return None

    token_data = decode_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        return None

    user = await get_user_by_id(db, token_data.user_id)
    return user


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require valid authentication - raises 401 if not authenticated."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_data = decode_token(credentials.credentials)
    if not token_data or not token_data.user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user_by_id(db, token_data.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def require_admin(user: User = Depends(require_auth)) -> User:
    """Require admin privileges - raises 403 if not admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def check_project_access(
    project_id: str,
    user: User,
    db: AsyncSession,
    required_role: str | None = None,
) -> Project:
    """
    Check if user has access to project.

    Args:
        project_id: Project ID to check
        user: Authenticated user
        db: Database session
        required_role: Optional minimum role required (owner, admin, member, viewer)

    Returns:
        Project if access granted

    Raises:
        HTTPException: 404 if project not found, 403 if access denied
    """
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if user is owner
    if project.owner_id == user.id:
        return project

    # Check if user is member
    member_result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user.id
        )
    )
    member = member_result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=403, detail="Access denied to this project")

    # Check role hierarchy if required
    if required_role:
        role_hierarchy = {"owner": 4, "admin": 3, "member": 2, "viewer": 1}
        user_level = role_hierarchy.get(member.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_level < required_level:
            raise HTTPException(status_code=403, detail=f"Requires {required_role} role or higher")

    return project


def get_user_project_role(project: Project, user: User, member: ProjectMember | None) -> str:
    """Get user's role in a project."""
    if project.owner_id == user.id:
        return "owner"
    if member:
        return member.role
    return "none"


async def get_user_projects(user: User, db: AsyncSession) -> list[Project]:
    """
    Get all projects user has access to.

    Returns projects where user is owner or member.
    """
    # Get owned projects
    owned_result = await db.execute(select(Project).where(Project.owner_id == user.id))
    owned = list(owned_result.scalars().all())

    # Get member projects
    member_result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
    )
    member_projects = list(member_result.scalars().all())

    # Combine and deduplicate
    all_projects = {p.id: p for p in owned + member_projects}
    return list(all_projects.values())


async def get_default_project(user: User, db: AsyncSession) -> Project | None:
    """
    Get user's default project (first owned or first member project).

    Used when project_id is not specified in request.
    """
    # Prefer owned project
    owned_result = await db.execute(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at).limit(1)
    )
    owned = owned_result.scalar_one_or_none()
    if owned:
        return owned

    # Fallback to member project
    member_result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(ProjectMember.added_at)
        .limit(1)
    )
    return member_result.scalar_one_or_none()
