"""
Projects Router - API Endpoints for projects, folders, members.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.project_service import ProjectService
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    FolderCreate, FolderUpdate, FolderResponse,
    MemberAdd, MemberUpdate, MemberResponse
)

router = APIRouter(prefix="/projects", tags=["projects"])


def get_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


# === Project Endpoints ===

@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Create new project."""
    return await service.create_project(data, user.id)


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """List all projects user has access to."""
    return await service.get_user_projects(user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Get project by ID."""
    return await service.get_project(project_id, user.id)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Update project."""
    return await service.update_project(project_id, data, user.id)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Delete project."""
    await service.delete_project(project_id, user.id)
    return {"status": "deleted"}


# === Folder Endpoints ===

@router.post("/{project_id}/folders", response_model=FolderResponse)
async def create_folder(
    project_id: str,
    data: FolderCreate,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Create folder in project."""
    return await service.create_folder(project_id, data, user.id)


@router.get("/{project_id}/folders", response_model=List[FolderResponse])
async def list_folders(
    project_id: str,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """List all folders in project."""
    return await service.get_folders(project_id, user.id)


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    data: FolderUpdate,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Update folder."""
    return await service.update_folder(folder_id, data, user.id)


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Delete folder."""
    await service.delete_folder(folder_id, user.id)
    return {"status": "deleted"}


# === Member Endpoints ===

@router.post("/{project_id}/members", response_model=MemberResponse)
async def add_member(
    project_id: str,
    data: MemberAdd,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Add member to project."""
    member = await service.add_member(project_id, data, user.id)
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        username=member.user.username if member.user else "unknown",
        role=member.role,
        added_at=member.added_at
    )


@router.get("/{project_id}/members", response_model=List[MemberResponse])
async def list_members(
    project_id: str,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """List all members of project."""
    members = await service.get_members(project_id, user.id)
    return [
        MemberResponse(
            id=m.id,
            user_id=m.user_id,
            username=m.user.username if m.user else "unknown",
            role=m.role,
            added_at=m.added_at
        )
        for m in members
    ]


@router.put("/{project_id}/members/{member_user_id}", response_model=MemberResponse)
async def update_member(
    project_id: str,
    member_user_id: str,
    data: MemberUpdate,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Update member role."""
    member = await service.update_member(project_id, member_user_id, data, user.id)
    return MemberResponse(
        id=member.id,
        user_id=member.user_id,
        username=member.user.username if member.user else "unknown",
        role=member.role,
        added_at=member.added_at
    )


@router.delete("/{project_id}/members/{member_user_id}")
async def remove_member(
    project_id: str,
    member_user_id: str,
    user: User = Depends(require_auth),
    service: ProjectService = Depends(get_service)
):
    """Remove member from project."""
    await service.remove_member(project_id, member_user_id, user.id)
    return {"status": "removed"}
