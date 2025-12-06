"""
TestCase Repository for test case data access.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TestCase
from app.repositories.base import BaseRepository


class TestCaseRepository(BaseRepository[TestCase]):
    """Repository for TestCase model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(TestCase, session)

    async def get_by_session(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestCase]:
        """Get all test cases linked to a session."""
        return await self.get_many_by_field("session_id", session_id, skip, limit)

    async def get_by_folder(
        self,
        folder: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestCase]:
        """Get test cases in a specific folder."""
        query = (
            select(TestCase)
            .where(TestCase.folder == folder)
            .order_by(desc(TestCase.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestCase]:
        """Get test cases by status."""
        return await self.get_many_by_field("status", status, skip, limit)

    async def get_by_priority(
        self,
        priority: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TestCase]:
        """Get test cases by priority."""
        return await self.get_many_by_field("priority", priority, skip, limit)

    async def search(
        self,
        query_text: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TestCase]:
        """Search test cases by title or description."""
        search_pattern = f"%{query_text}%"
        query = (
            select(TestCase)
            .where(
                or_(
                    TestCase.title.ilike(search_pattern),
                    TestCase.description.ilike(search_pattern),
                )
            )
            .order_by(desc(TestCase.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TestCase]:
        """
        Get test cases by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, require all tags; if False, match any tag
        """
        # For JSON array containment, we need database-specific approach
        # This is a simplified version that works with SQLite
        query = select(TestCase)

        # Get all and filter in Python for SQLite compatibility
        result = await self.session.execute(query)
        all_cases = list(result.scalars().all())

        filtered = []
        for tc in all_cases:
            tc_tags = tc.tags or []
            if match_all:
                if all(tag in tc_tags for tag in tags):
                    filtered.append(tc)
            else:
                if any(tag in tc_tags for tag in tags):
                    filtered.append(tc)

        return filtered[skip : skip + limit]

    async def create_from_session(
        self,
        session_id: str,
        title: str,
        steps: list[dict[str, Any]],
        **kwargs,
    ) -> TestCase:
        """Create test case from session analysis."""
        return await self.create(
            {
                "session_id": session_id,
                "title": title,
                "steps": steps,
                "status": kwargs.get("status", "Draft"),
                "priority": kwargs.get("priority", "Medium"),
                "description": kwargs.get("description"),
                "preconditions": kwargs.get("preconditions"),
                "postconditions": kwargs.get("postconditions"),
                "tags": kwargs.get("tags", []),
                "folder": kwargs.get("folder"),
                "created_by": kwargs.get("created_by"),
            }
        )

    async def update_status(self, testcase_id: str, status: str) -> TestCase | None:
        """Update test case status."""
        return await self.update(
            testcase_id,
            {
                "status": status,
                "updated_at": datetime.utcnow(),
            },
        )

    async def update_automation_status(
        self,
        testcase_id: str,
        automation_status: str,
    ) -> TestCase | None:
        """Update automation status."""
        return await self.update(
            testcase_id,
            {
                "automation_status": automation_status,
                "updated_at": datetime.utcnow(),
            },
        )

    async def link_external(
        self,
        testcase_id: str,
        external_id: str,
        external_url: str,
    ) -> TestCase | None:
        """Link test case to external system."""
        return await self.update(
            testcase_id,
            {
                "external_id": external_id,
                "external_url": external_url,
                "updated_at": datetime.utcnow(),
            },
        )

    async def get_stats(self) -> dict[str, Any]:
        """Get test case statistics."""
        # Total count
        total = await self.count()

        # By status
        status_query = select(TestCase.status, func.count()).group_by(TestCase.status)
        status_result = await self.session.execute(status_query)
        by_status = {row[0]: row[1] for row in status_result.all()}

        # By priority
        priority_query = select(TestCase.priority, func.count()).group_by(TestCase.priority)
        priority_result = await self.session.execute(priority_query)
        by_priority = {row[0]: row[1] for row in priority_result.all()}

        # By automation status
        automation_query = select(TestCase.automation_status, func.count()).group_by(
            TestCase.automation_status
        )
        automation_result = await self.session.execute(automation_query)
        by_automation = {row[0]: row[1] for row in automation_result.all()}

        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_automation": by_automation,
        }

    async def get_folders(self) -> list[str]:
        """Get all unique folder names."""
        query = select(TestCase.folder).where(TestCase.folder.isnot(None)).distinct()
        result = await self.session.execute(query)
        return [row[0] for row in result.all() if row[0]]
