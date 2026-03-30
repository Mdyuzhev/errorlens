"""TestCase service - business logic layer."""

from datetime import datetime
from typing import Any

from sqlalchemy import cast, func, String, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TestCase
from app.repositories.testcase_repo import TestCaseRepository
from app.services import event_publisher
from app.services.project_service import ProjectService

# Valid values
VALID_STATUSES = ["Draft", "Ready", "Approved", "Deprecated"]
VALID_PRIORITIES = ["Low", "Medium", "High", "Critical"]
VALID_AUTOMATION = ["Manual", "Automated", "To Automate"]


class TestCaseService:
    """Service for test case business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TestCaseRepository(db)

    async def create_testcase(
        self,
        title: str,
        created_by: str,
        description: str | None = None,
        preconditions: str | None = None,
        postconditions: str | None = None,
        priority: str = "Medium",
        status: str = "Draft",
        automation_status: str = "Manual",
        folder: str | None = None,
        folder_id: str | None = None,
        tags: list[str] | None = None,
        steps: list[dict] | None = None,
        session_id: str | None = None,
        project_id: str | None = None,
    ) -> TestCase:
        """Create new test case."""
        # Validate enums
        if status not in VALID_STATUSES:
            status = "Draft"
        if priority not in VALID_PRIORITIES:
            priority = "Medium"
        if automation_status not in VALID_AUTOMATION:
            automation_status = "Manual"

        testcase_data = {
            "title": title,
            "description": description,
            "preconditions": preconditions,
            "postconditions": postconditions,
            "priority": priority,
            "status": status,
            "automation_status": automation_status,
            "folder": folder,
            "folder_id": folder_id,
            "tags": tags or [],
            "steps": steps or [],
            "session_id": session_id,
            "created_by": created_by,
            "project_id": project_id,
        }

        # Generate human_id if project has a key
        if project_id:
            project_service = ProjectService(self.db)
            human_id = await project_service.next_human_id(project_id)
            if human_id:
                testcase_data["human_id"] = human_id

        testcase = await self.repo.create(testcase_data)
        await self.db.commit()

        await event_publisher.publish(
            "testcase.created",
            {"id": testcase.id, "title": title, "priority": priority, "folder_id": folder_id},
            project_id=project_id,
        )

        return testcase

    async def get_testcase(self, testcase_id: str) -> TestCase | None:
        """Get test case by ID."""
        return await self.repo.get_by_id(testcase_id)

    async def list_testcases(
        self,
        folder: str | None = None,
        folder_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        linked_issue_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List test cases with filters."""
        if linked_issue_id:
            query = (
                select(TestCase)
                .where(cast(TestCase.linked_issue_ids, String).contains(linked_issue_id))
                .order_by(TestCase.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await self.db.execute(query)
            testcases = result.scalars().all()
        elif folder_id:
            testcases = await self.repo.get_by_folder_id(folder_id, skip=offset, limit=limit)
        elif folder:
            testcases = await self.repo.get_by_folder(folder, skip=offset, limit=limit)
        elif status:
            testcases = await self.repo.get_by_status(status, skip=offset, limit=limit)
        elif priority:
            testcases = await self.repo.get_by_priority(priority, skip=offset, limit=limit)
        else:
            testcases = await self.repo.get_all(
                skip=offset, limit=limit, order_by=TestCase.created_at.desc()
            )

        return [self._to_list_dict(tc) for tc in testcases]

    async def search_testcases(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search test cases by title or description."""
        testcases = await self.repo.search(query, skip=offset, limit=limit)
        return [self._to_list_dict(tc) for tc in testcases]

    async def get_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
    ) -> list[dict[str, Any]]:
        """Get test cases by tags."""
        testcases = await self.repo.get_by_tags(tags, match_all=match_all)
        return [self._to_list_dict(tc) for tc in testcases]

    async def get_folders(self) -> list[str]:
        """Get unique folders."""
        return await self.repo.get_folders()

    async def get_stats(self) -> dict[str, Any]:
        """Get test case statistics."""
        return await self.repo.get_stats()

    async def count_testcases(
        self,
        folder_id: str | None = None,
        folder: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        q: str | None = None,
    ) -> int:
        """Count test cases matching filters."""
        query = select(func.count(TestCase.id))
        if folder_id:
            query = query.where(TestCase.folder_id == folder_id)
        elif folder:
            query = query.where(TestCase.folder == folder)
        if status:
            query = query.where(TestCase.status == status)
        if priority:
            query = query.where(TestCase.priority == priority)
        if q:
            query = query.where(TestCase.title.ilike(f'%{q}%'))

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update_testcase(self, testcase_id: str, **updates) -> TestCase | None:
        """Update test case fields."""
        testcase = await self.repo.get_by_id(testcase_id)
        if not testcase:
            return None

        old_status = testcase.status

        for key, value in updates.items():
            if value is not None:
                setattr(testcase, key, value)

        testcase.updated_at = datetime.utcnow()
        await self.db.commit()

        new_status = updates.get("status")
        if new_status and new_status != old_status:
            await event_publisher.publish(
                "testcase.status_changed",
                {
                    "id": testcase.id, "title": testcase.title,
                    "old_status": old_status, "new_status": new_status,
                },
                project_id=testcase.project_id,
            )

        return testcase

    async def update_status(self, testcase_id: str, status: str) -> TestCase | None:
        """Update test case status."""
        if status not in VALID_STATUSES:
            return None
        result = await self.repo.update_status(testcase_id, status)
        await self.db.commit()
        return result

    async def update_automation_status(
        self, testcase_id: str, automation_status: str
    ) -> TestCase | None:
        """Update automation status."""
        if automation_status not in VALID_AUTOMATION:
            return None
        result = await self.repo.update_automation_status(testcase_id, automation_status)
        await self.db.commit()
        return result

    async def delete_testcase(self, testcase_id: str) -> bool:
        """Delete test case by ID."""
        testcase = await self.repo.get_by_id(testcase_id)
        title = testcase.title if testcase else ""
        project_id = testcase.project_id if testcase else None

        deleted = await self.repo.delete(testcase_id)
        if deleted:
            await self.db.commit()
            await event_publisher.publish(
                "testcase.deleted",
                {"id": testcase_id, "title": title},
                project_id=project_id,
            )
        return deleted

    async def link_to_external(
        self,
        testcase_id: str,
        external_id: str,
        external_url: str,
    ) -> TestCase | None:
        """Link test case to external system (e.g., TestIT)."""
        result = await self.repo.link_external(testcase_id, external_id, external_url)
        await self.db.commit()
        return result

    def _to_list_dict(self, tc: TestCase) -> dict[str, Any]:
        """Convert test case to list response dict."""
        return {
            "id": tc.id,
            "human_id": tc.human_id,
            "title": tc.title,
            "description": tc.description,
            "preconditions": tc.preconditions,
            "postconditions": tc.postconditions,
            "priority": tc.priority,
            "status": tc.status,
            "automation_status": tc.automation_status,
            "folder": tc.folder,
            "folder_id": tc.folder_id,
            "tags": tc.tags,
            "steps": tc.steps,
            "linked_issue_ids": tc.linked_issue_ids,
            "linked_article_ids": tc.linked_article_ids,
            "created_at": tc.created_at.isoformat() if tc.created_at else None,
            "created_by": tc.created_by,
            "updated_at": tc.updated_at.isoformat() if tc.updated_at else tc.created_at.isoformat() if tc.created_at else None,
        }

    def to_detail_dict(self, tc: TestCase) -> dict[str, Any]:
        """Convert test case to detailed response dict."""
        result = self._to_list_dict(tc)
        result["session_id"] = tc.session_id
        result["external_id"] = tc.external_id
        result["external_url"] = tc.external_url
        result["updated_at"] = tc.updated_at.isoformat() if tc.updated_at else None
        return result
