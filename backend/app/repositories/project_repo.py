"""
Project Repository - Data access for projects, folders, members.
"""
from typing import List, Optional
from sqlalchemy import select, func, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.db_models import Project, Folder, ProjectMember, Session


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Project, db)

    async def get_by_slug(self, slug: str) -> Optional[Project]:
        """Get project by slug."""
        result = await self.session.execute(
            select(Project).where(Project.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: str) -> List[Project]:
        """Get all projects owned by user."""
        result = await self.session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_projects(self, user_id: str) -> List[Project]:
        """Get all projects where user is owner or member."""
        # Projects where user is owner
        owned_query = select(Project).where(Project.owner_id == user_id)

        # Projects where user is member
        member_query = (
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(ProjectMember.user_id == user_id)
        )

        # Union both queries
        union_query = union(owned_query, member_query).order_by(Project.created_at.desc())
        result = await self.session.execute(select(Project).from_statement(union_query))
        return list(result.scalars().all())

    async def get_with_stats(self, project_id: str) -> Optional[dict]:
        """Get project with member/folder/session counts."""
        project = await self.get_by_id(project_id)
        if not project:
            return None

        # Count members
        members_result = await self.session.execute(
            select(func.count(ProjectMember.id))
            .where(ProjectMember.project_id == project_id)
        )
        members_count = members_result.scalar() or 0

        # Count folders
        folders_result = await self.session.execute(
            select(func.count(Folder.id))
            .where(Folder.project_id == project_id)
        )
        folders_count = folders_result.scalar() or 0

        # Count sessions
        sessions_result = await self.session.execute(
            select(func.count(Session.id))
            .where(Session.project_id == project_id)
        )
        sessions_count = sessions_result.scalar() or 0

        return {
            "project": project,
            "members_count": members_count,
            "folders_count": folders_count,
            "sessions_count": sessions_count,
        }

    async def count_user_projects(self, user_id: str) -> int:
        """Count projects owned by user."""
        result = await self.session.execute(
            select(func.count(Project.id))
            .where(Project.owner_id == user_id)
        )
        return result.scalar() or 0


class FolderRepository(BaseRepository[Folder]):
    """Repository for Folder operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Folder, db)

    async def get_by_project(self, project_id: str) -> List[Folder]:
        """Get all folders in project."""
        result = await self.session.execute(
            select(Folder)
            .where(Folder.project_id == project_id)
            .order_by(Folder.sort_order)
        )
        return list(result.scalars().all())

    async def get_children(self, parent_id: str) -> List[Folder]:
        """Get child folders."""
        result = await self.session.execute(
            select(Folder)
            .where(Folder.parent_id == parent_id)
            .order_by(Folder.sort_order)
        )
        return list(result.scalars().all())

    async def count_in_project(self, project_id: str) -> int:
        """Count folders in project."""
        result = await self.session.execute(
            select(func.count(Folder.id))
            .where(Folder.project_id == project_id)
        )
        return result.scalar() or 0


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    """Repository for ProjectMember operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(ProjectMember, db)

    async def get_by_project(self, project_id: str) -> List[ProjectMember]:
        """Get all members of project."""
        result = await self.session.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
        )
        return list(result.scalars().all())

    async def get_member(self, project_id: str, user_id: str) -> Optional[ProjectMember]:
        """Get specific member."""
        result = await self.session.execute(
            select(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def count_in_project(self, project_id: str) -> int:
        """Count members in project."""
        result = await self.session.execute(
            select(func.count(ProjectMember.id))
            .where(ProjectMember.project_id == project_id)
        )
        return result.scalar() or 0

    async def is_member(self, project_id: str, user_id: str) -> bool:
        """Check if user is member of project."""
        member = await self.get_member(project_id, user_id)
        return member is not None
