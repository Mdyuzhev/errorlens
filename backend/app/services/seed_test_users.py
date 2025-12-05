"""Seed test users for smoke testing."""

import asyncio
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_context
from app.models.user import User
from app.models.db_models import Project, ProjectMember
from app.services.auth import get_password_hash


# Test users configuration
TEST_USERS: List[Dict[str, Any]] = [
    {"username": "owner1", "password": "Test123!", "is_admin": False},
    {"username": "owner2", "password": "Test123!", "is_admin": False},
    {"username": "admin1", "password": "Test123!", "is_admin": False},
    {"username": "member1", "password": "Test123!", "is_admin": False},
    {"username": "viewer1", "password": "Test123!", "is_admin": False},
    {"username": "viewer2", "password": "Test123!", "is_admin": False},
]

# Test projects configuration
TEST_PROJECTS = [
    {"name": "Project Alpha", "slug": "project-alpha", "owner_username": "owner1"},
    {"name": "Project Beta", "slug": "project-beta", "owner_username": "owner2"},
]

# Project memberships (role assignments)
PROJECT_MEMBERSHIPS = [
    # Project Alpha members
    {"project_slug": "project-alpha", "username": "admin1", "role": "admin"},
    {"project_slug": "project-alpha", "username": "member1", "role": "member"},
    {"project_slug": "project-alpha", "username": "viewer1", "role": "viewer"},
    # Project Beta members
    {"project_slug": "project-beta", "username": "viewer2", "role": "viewer"},
]


async def seed_test_users(db: AsyncSession) -> Dict[str, Any]:
    """
    Seed test users and projects for smoke testing.

    Returns:
        Dict with created users and projects info
    """
    result = {
        "users_created": [],
        "users_skipped": [],
        "projects_created": [],
        "projects_skipped": [],
        "memberships_created": [],
    }

    # Cache for lookups
    user_cache: Dict[str, User] = {}
    project_cache: Dict[str, Project] = {}

    # 1. Create users
    for user_data in TEST_USERS:
        existing = await db.execute(
            select(User).where(User.username == user_data["username"])
        )
        user = existing.scalar_one_or_none()

        if user:
            result["users_skipped"].append(user_data["username"])
            user_cache[user_data["username"]] = user
        else:
            user = User(
                username=user_data["username"],
                email=f"{user_data['username']}@test.local",
                hashed_password=get_password_hash(user_data["password"]),
                is_active=True,
                is_admin=user_data["is_admin"],
                display_name=user_data["username"].replace("_", " ").title(),
            )
            db.add(user)
            await db.flush()
            result["users_created"].append(user_data["username"])
            user_cache[user_data["username"]] = user

    # 2. Create projects
    for proj_data in TEST_PROJECTS:
        existing = await db.execute(
            select(Project).where(Project.slug == proj_data["slug"])
        )
        project = existing.scalar_one_or_none()

        if project:
            result["projects_skipped"].append(proj_data["slug"])
            project_cache[proj_data["slug"]] = project
        else:
            owner = user_cache.get(proj_data["owner_username"])
            if not owner:
                continue

            project = Project(
                name=proj_data["name"],
                slug=proj_data["slug"],
                description=f"Test project: {proj_data['name']}",
                owner_id=owner.id,
                plan="free",
                is_public=False,
            )
            db.add(project)
            await db.flush()
            result["projects_created"].append(proj_data["slug"])
            project_cache[proj_data["slug"]] = project

            # Owner gets "owner" role membership automatically
            owner_membership = ProjectMember(
                project_id=project.id,
                user_id=owner.id,
                role="owner",
            )
            db.add(owner_membership)

    # 3. Create memberships
    for membership_data in PROJECT_MEMBERSHIPS:
        project = project_cache.get(membership_data["project_slug"])
        user = user_cache.get(membership_data["username"])

        if not project or not user:
            continue

        # Check if membership exists
        existing = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id,
                ProjectMember.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        membership = ProjectMember(
            project_id=project.id,
            user_id=user.id,
            role=membership_data["role"],
        )
        db.add(membership)
        result["memberships_created"].append(
            f"{membership_data['username']}@{membership_data['project_slug']}:{membership_data['role']}"
        )

    await db.commit()
    return result


async def clear_test_users(db: AsyncSession) -> Dict[str, int]:
    """
    Remove all test users and their projects.

    Returns:
        Dict with counts of deleted entities
    """
    result = {"users_deleted": 0, "projects_deleted": 0}

    # Get test usernames
    test_usernames = [u["username"] for u in TEST_USERS]

    # Delete projects owned by test users
    for proj_data in TEST_PROJECTS:
        existing = await db.execute(
            select(Project).where(Project.slug == proj_data["slug"])
        )
        project = existing.scalar_one_or_none()
        if project:
            await db.delete(project)
            result["projects_deleted"] += 1

    # Delete test users
    for username in test_usernames:
        existing = await db.execute(
            select(User).where(User.username == username)
        )
        user = existing.scalar_one_or_none()
        if user:
            await db.delete(user)
            result["users_deleted"] += 1

    await db.commit()
    return result


async def seed_test_users_standalone():
    """Standalone function to run seeding."""
    async with get_db_context() as db:
        result = await seed_test_users(db)
        print("Test users seeding completed!")
        print(f"  Users created: {result['users_created']}")
        print(f"  Users skipped: {result['users_skipped']}")
        print(f"  Projects created: {result['projects_created']}")
        print(f"  Projects skipped: {result['projects_skipped']}")
        print(f"  Memberships created: {result['memberships_created']}")
        return result


if __name__ == "__main__":
    asyncio.run(seed_test_users_standalone())
