"""
Project Service - Business Logic for projects, folders, members.
"""

import logging
import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Folder, Project, ProjectMember
from app.repositories.project_repo import (
    FolderRepository,
    ProjectMemberRepository,
    ProjectRepository,
)
from app.repositories.user_repo import UserRepository
from app.schemas.project import (
    FolderCreate,
    FolderUpdate,
    MemberAdd,
    MemberRole,
    MemberUpdate,
    ProjectCreate,
    ProjectPlan,
    ProjectUpdate,
    get_plan_limits,
)

logger = logging.getLogger(__name__)


def validate_key(key: str) -> str:
    """Validate project key: 2-4 uppercase letters only."""
    key = key.strip().upper()
    if not re.match(r"^[A-Z]{2,4}$", key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key must be 2-4 uppercase letters",
        )
    return key


def suggest_key(name: str) -> str:
    """Auto-suggest project key from name."""
    words = re.findall(r"[a-zA-Z]+", name)
    if len(words) >= 2:
        key = "".join(w[0] for w in words[:4]).upper()
    elif words:
        key = words[0][:3].upper()
    else:
        key = "PRJ"
    key = re.sub(r"[^A-Z]", "", key)
    if len(key) < 2:
        key = "PRJ"
    return key[:4]


def generate_slug(name: str) -> str:
    """Generate URL-safe slug from name."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:50]


class ProjectService:
    """Service for project business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.folder_repo = FolderRepository(db)
        self.member_repo = ProjectMemberRepository(db)
        self.user_repo = UserRepository(db)

    # === Project Operations ===

    async def create_project(self, data: ProjectCreate, owner_id: str) -> Project:
        """Create new project."""
        user = await self.user_repo.get_by_id(owner_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check limits
        project_count = await self.project_repo.count_user_projects(owner_id)
        limits = get_plan_limits(ProjectPlan.FREE)  # TODO: get user's plan

        is_admin = getattr(user, 'is_superuser', False) or getattr(user, 'role', '') == 'admin'
        if project_count >= limits.max_projects and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Project limit reached ({limits.max_projects}). Upgrade to PRO.",
            )

        # Generate unique slug
        base_slug = generate_slug(data.name)
        slug = base_slug
        counter = 1
        while await self.project_repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Resolve project key
        project_key = await self._resolve_key(data.key, data.name)

        # Create project
        project = Project(
            name=data.name,
            slug=slug,
            description=data.description,
            owner_id=owner_id,
            plan=ProjectPlan.FREE,
            key=project_key,
            entity_counter=0,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        # Seed default task types, statuses, and transitions
        from app.services.task_workflow_service import TaskWorkflowService
        workflow_service = TaskWorkflowService(self.db)
        await workflow_service.seed_defaults(project.id)
        await self.db.commit()

        logger.info(f"Created project {project.id} for user {owner_id}")
        return project

    async def get_project(self, project_id: str, user_id: str) -> Project:
        """Get project if user has access."""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not await self._has_access(project, user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        return project

    async def get_user_projects(self, user_id: str) -> list[Project]:
        """Get all projects user has access to."""
        return await self.project_repo.get_user_projects(user_id)

    async def update_project(self, project_id: str, data: ProjectUpdate, user_id: str) -> Project:
        """Update project (owner/admin only)."""
        project = await self.get_project(project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role not in [MemberRole.OWNER, MemberRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only owner/admin can update project")

        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description

        project.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(project)

        logger.info(f"Updated project {project_id}")
        return project

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete project (owner only)."""
        project = await self.get_project(project_id, user_id)

        if project.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Only owner can delete project")

        await self.db.delete(project)
        await self.db.commit()

        logger.info(f"Deleted project {project_id}")
        return True

    # === Folder Operations ===

    async def create_folder(self, project_id: str, data: FolderCreate, user_id: str) -> Folder:
        """Create folder in project."""
        project = await self.get_project(project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role == MemberRole.VIEWER:
            raise HTTPException(status_code=403, detail="Viewers cannot create folders")

        # Check limits
        limits = get_plan_limits(project.plan)
        folder_count = await self.folder_repo.count_in_project(project_id)

        if folder_count >= limits.max_folders_per_project:
            raise HTTPException(
                status_code=403,
                detail=f"Folder limit reached ({limits.max_folders_per_project}). Upgrade to PRO.",
            )

        folder = Folder(
            name=data.name,
            project_id=project_id,
            parent_id=data.parent_id,
            sort_order=folder_count + 1,
        )
        self.db.add(folder)
        await self.db.commit()
        await self.db.refresh(folder)

        logger.info(f"Created folder {folder.id} in project {project_id}")
        return folder

    async def get_folders(self, project_id: str, user_id: str) -> list[Folder]:
        """Get all folders in project."""
        await self.get_project(project_id, user_id)  # Check access
        return await self.folder_repo.get_by_project(project_id)

    async def update_folder(self, folder_id: str, data: FolderUpdate, user_id: str) -> Folder:
        """Update folder."""
        folder = await self.folder_repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        project = await self.get_project(folder.project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role == MemberRole.VIEWER:
            raise HTTPException(status_code=403, detail="Viewers cannot update folders")

        if data.name is not None:
            folder.name = data.name
        if data.parent_id is not None:
            folder.parent_id = data.parent_id

        await self.db.commit()
        await self.db.refresh(folder)

        logger.info(f"Updated folder {folder_id}")
        return folder

    async def delete_folder(self, folder_id: str, user_id: str) -> bool:
        """Delete folder."""
        folder = await self.folder_repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        project = await self.get_project(folder.project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role not in [MemberRole.OWNER, MemberRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only owner/admin can delete folders")

        await self.db.delete(folder)
        await self.db.commit()

        logger.info(f"Deleted folder {folder_id}")
        return True

    # === Member Operations ===

    async def add_member(self, project_id: str, data: MemberAdd, user_id: str) -> ProjectMember:
        """Add member to project."""
        project = await self.get_project(project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role not in [MemberRole.OWNER, MemberRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only owner/admin can add members")

        # Check limits
        limits = get_plan_limits(project.plan)
        member_count = await self.member_repo.count_in_project(project_id)

        if member_count >= limits.max_members_per_project:
            raise HTTPException(
                status_code=403,
                detail=f"Member limit reached ({limits.max_members_per_project}). Upgrade to PRO.",
            )

        # Find user
        target_user = await self.user_repo.get_by_username(data.username)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if already member
        if await self.member_repo.is_member(project_id, target_user.id):
            raise HTTPException(status_code=400, detail="User is already a member")

        # Cannot add as owner
        if data.role == MemberRole.OWNER:
            raise HTTPException(status_code=400, detail="Cannot add as owner")

        member = ProjectMember(
            project_id=project_id, user_id=target_user.id, role=data.role, added_by_id=user_id
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)

        logger.info(f"Added member {target_user.id} to project {project_id}")
        return member

    async def get_members(self, project_id: str, user_id: str) -> list[ProjectMember]:
        """Get all members of project."""
        await self.get_project(project_id, user_id)  # Check access
        return await self.member_repo.get_by_project(project_id)

    async def update_member(
        self, project_id: str, member_user_id: str, data: MemberUpdate, user_id: str
    ) -> ProjectMember:
        """Update member role."""
        project = await self.get_project(project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role not in [MemberRole.OWNER, MemberRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only owner/admin can update members")

        if data.role == MemberRole.OWNER:
            raise HTTPException(status_code=400, detail="Cannot change role to owner")

        member = await self.member_repo.get_member(project_id, member_user_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        member.role = data.role
        await self.db.commit()
        await self.db.refresh(member)

        logger.info(f"Updated member {member_user_id} role to {data.role} in project {project_id}")
        return member

    async def remove_member(self, project_id: str, member_user_id: str, user_id: str) -> bool:
        """Remove member from project."""
        project = await self.get_project(project_id, user_id)

        role = await self._get_user_role(project, user_id)
        if role not in [MemberRole.OWNER, MemberRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Only owner/admin can remove members")

        if member_user_id == project.owner_id:
            raise HTTPException(status_code=400, detail="Cannot remove project owner")

        member = await self.member_repo.get_member(project_id, member_user_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        await self.db.delete(member)
        await self.db.commit()

        logger.info(f"Removed member {member_user_id} from project {project_id}")
        return True

    # === Helper Methods ===

    async def _has_access(self, project: Project, user_id: str) -> bool:
        """Check if user has access to project."""
        if project.owner_id == user_id:
            return True
        return await self.member_repo.is_member(project.id, user_id)

    async def _get_user_role(self, project: Project, user_id: str) -> MemberRole:
        """Get user's role in project."""
        if project.owner_id == user_id:
            return MemberRole.OWNER

        member = await self.member_repo.get_member(project.id, user_id)
        if member:
            return member.role

        raise HTTPException(status_code=403, detail="Access denied")

    async def _resolve_key(self, key: str | None, name: str) -> str | None:
        """Resolve and validate project key, ensuring uniqueness."""
        if key:
            key = validate_key(key)
            if await self.project_repo.get_by_key(key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Key '{key}' is already taken",
                )
            return key

        # Auto-suggest from name
        base_key = suggest_key(name)
        candidate = base_key
        suffix = 2
        while await self.project_repo.get_by_key(candidate):
            candidate = f"{base_key}{suffix}"[:4]
            suffix += 1
            if suffix > 99:
                return None
        return candidate

    async def next_human_id(self, project_id: str) -> str | None:
        """Generate next human-readable ID for entity in project.

        Uses SELECT ... FOR UPDATE to prevent concurrent duplicates.
        """
        result = await self.db.execute(
            select(Project).where(Project.id == project_id).with_for_update()
        )
        project = result.scalar_one_or_none()
        if not project or not project.key:
            return None

        project.entity_counter += 1
        await self.db.flush()
        return f"{project.key}-{project.entity_counter}"

    async def check_key_available(self, key: str) -> dict:
        """Check if key is available and suggest alternative."""
        try:
            key = validate_key(key)
        except HTTPException:
            return {"available": False, "suggestion": None}

        existing = await self.project_repo.get_by_key(key)
        if not existing:
            return {"available": True, "suggestion": key}

        # Suggest alternative
        base = key
        suffix = 2
        while True:
            candidate = f"{base}{suffix}"[:4]
            if not await self.project_repo.get_by_key(candidate):
                return {"available": False, "suggestion": candidate}
            suffix += 1
            if suffix > 99:
                return {"available": False, "suggestion": None}
