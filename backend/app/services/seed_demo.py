"""Seed demo data for ErrorLens."""

import asyncio
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import get_db_context
from app.models.db_models import (
    Article,
    ArticleFolder,
    Project,
    ProjectMember,
    Task,
    TestCase,
    TestCaseFolder,
)
from app.models.user import User
from app.services.seed_demo_constants import (
    DEMO_ARTICLE_FOLDERS,
    DEMO_ARTICLES,
    DEMO_TASKS,
    DEMO_TEST_CASES,
    DEMO_TESTCASE_FOLDERS,
    WELCOME_ARTICLE,
)


async def _get_demo_project_id(db) -> str | None:
    """Get project_id for demo user's default project."""
    user_result = await db.execute(
        select(User).where(User.username == "demo")
    )
    demo_user = user_result.scalar_one_or_none()
    if not demo_user:
        return None

    project_result = await db.execute(
        select(Project).where(Project.owner_id == demo_user.id).limit(1)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        member_result = await db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == demo_user.id)
            .limit(1)
        )
        project = member_result.scalar_one_or_none()

    return project.id if project else None


async def _seed_testcases(db, project_id: str | None) -> None:
    """Seed demo test cases with folder tree."""
    folder_map: dict[str, str] = {}
    if project_id:
        existing_folders = await db.execute(select(TestCaseFolder).limit(1))
        if not existing_folders.scalar():
            for folder_name, subfolders in DEMO_TESTCASE_FOLDERS.items():
                parent = TestCaseFolder(
                    name=folder_name,
                    project_id=project_id,
                    sort_order=len(folder_map),
                )
                db.add(parent)
                await db.flush()
                folder_map[folder_name] = parent.id

                for i, sub_name in enumerate(subfolders):
                    child = TestCaseFolder(
                        name=sub_name,
                        parent_id=parent.id,
                        project_id=project_id,
                        sort_order=i,
                    )
                    db.add(child)
            await db.flush()
            print(f"Added {len(DEMO_TESTCASE_FOLDERS)} testcase folders with subfolders")

    for tc_data in DEMO_TEST_CASES:
        folder_id = folder_map.get(tc_data["folder"])
        tc = TestCase(
            title=tc_data["title"],
            description=tc_data["description"],
            preconditions=tc_data["preconditions"],
            postconditions=tc_data["postconditions"],
            priority=tc_data["priority"],
            status=tc_data["status"],
            automation_status=tc_data["automation_status"],
            folder=tc_data["folder"],
            folder_id=folder_id,
            project_id=project_id,
            tags=tc_data["tags"],
            steps=tc_data["steps"],
            created_by="demo",
        )
        db.add(tc)
    print(f"Added {len(DEMO_TEST_CASES)} demo test cases")


async def _seed_tasks(db) -> None:
    """Seed demo kanban tasks."""
    for i, task_data in enumerate(DEMO_TASKS):
        task = Task(
            title=task_data["title"],
            description=task_data["description"],
            status=task_data["status"],
            priority=task_data["priority"],
            labels=task_data["labels"],
            created_at=datetime.utcnow() - timedelta(days=len(DEMO_TASKS) - i),
        )
        if task_data["status"] == "done":
            task.completed_at = datetime.utcnow() - timedelta(days=1)
        db.add(task)
    print(f"Added {len(DEMO_TASKS)} demo tasks")


async def _seed_articles(db, project_id: str) -> None:
    """Seed welcome article + demo articles with folder tree."""
    # Welcome article
    article = Article(
        title=WELCOME_ARTICLE["title"],
        slug=WELCOME_ARTICLE["slug"],
        content=WELCOME_ARTICLE["content"],
        excerpt=WELCOME_ARTICLE["excerpt"],
        category=WELCOME_ARTICLE["category"],
        tags=WELCOME_ARTICLE["tags"],
        status=WELCOME_ARTICLE["status"],
        author=WELCOME_ARTICLE["author"],
        project_id=project_id,
        published_at=datetime.utcnow(),
    )
    db.add(article)

    # Create article folder tree
    article_folder_map: dict[str, str] = {}
    for folder_name, subfolders in DEMO_ARTICLE_FOLDERS.items():
        parent = ArticleFolder(
            name=folder_name,
            project_id=project_id,
        )
        db.add(parent)
        await db.flush()
        article_folder_map[folder_name] = parent.id

        for sub_name in subfolders:
            child = ArticleFolder(
                name=sub_name,
                parent_id=parent.id,
                project_id=project_id,
            )
            db.add(child)
            await db.flush()
            article_folder_map[sub_name] = child.id

    # Create demo articles
    for art_data in DEMO_ARTICLES:
        folder_id = article_folder_map.get(art_data["folder_key"])
        art = Article(
            title=art_data["title"],
            slug=art_data["slug"],
            content=art_data["content"],
            excerpt=art_data["excerpt"],
            category=art_data["category"],
            tags=art_data["tags"],
            status=art_data["status"],
            author=art_data["author"],
            folder_id=folder_id,
            project_id=project_id,
            published_at=datetime.utcnow(),
        )
        db.add(art)

    print(f"Added welcome article + {len(DEMO_ARTICLES)} demo articles in {len(article_folder_map)} folders")


async def seed_demo_data():
    """Seed demo test cases, tasks, and articles."""
    async with get_db_context() as db:
        # Testcases
        existing_cases = await db.execute(select(TestCase).limit(1))
        if existing_cases.scalar():
            print("Demo test cases already exist, skipping...")
        else:
            project_id = await _get_demo_project_id(db)
            await _seed_testcases(db, project_id)

        # Tasks
        existing_tasks = await db.execute(select(Task).limit(1))
        if existing_tasks.scalar():
            print("Demo tasks already exist, skipping...")
        else:
            await _seed_tasks(db)

        # Articles
        existing_articles = await db.execute(select(Article).where(Article.slug == "welcome"))
        if existing_articles.scalar():
            print("Welcome article already exists, skipping...")
        else:
            article_project_id = await _get_demo_project_id(db)
            if article_project_id:
                await _seed_articles(db, article_project_id)
            else:
                print("No project found, skipping articles")

        await db.commit()
        print("Demo data seeding completed!")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
