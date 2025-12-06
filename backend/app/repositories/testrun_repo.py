"""TestRun repository - data access layer."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TestRun
from app.repositories.base import BaseRepository


class TestRunRepository(BaseRepository[TestRun]):
    """Repository for TestRun CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(TestRun, db)

    async def get_recent(
        self,
        limit: int = 10,
        offset: int = 0,
        test_type: str | None = None,
        status: str | None = None,
    ) -> list[TestRun]:
        """Get recent test runs with optional filters."""
        query = select(TestRun).order_by(TestRun.started_at.desc())

        if test_type:
            query = query.where(TestRun.test_type == test_type)
        if status:
            query = query.where(TestRun.status == status)

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_completed(self, limit: int = 5) -> list[TestRun]:
        """Get completed test runs (passed or failed)."""
        query = (
            select(TestRun)
            .where(TestRun.status.in_(["passed", "failed"]))
            .order_by(TestRun.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[TestRun]:
        """Get test runs within date range."""
        query = (
            select(TestRun)
            .where(TestRun.started_at >= start_date)
            .where(TestRun.started_at <= end_date)
            .order_by(TestRun.started_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_stats(self, days: int = 30) -> dict[str, Any]:
        """Get test run statistics for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total runs
        total_query = select(func.count()).select_from(TestRun).where(TestRun.started_at >= cutoff)
        total_result = await self.session.execute(total_query)
        total_runs = total_result.scalar() or 0

        # By status
        status_query = (
            select(TestRun.status, func.count())
            .where(TestRun.started_at >= cutoff)
            .group_by(TestRun.status)
        )
        status_result = await self.session.execute(status_query)
        by_status = {row[0]: row[1] for row in status_result.all()}

        # By test type
        type_query = (
            select(TestRun.test_type, func.count())
            .where(TestRun.started_at >= cutoff)
            .group_by(TestRun.test_type)
        )
        type_result = await self.session.execute(type_query)
        by_type = {row[0]: row[1] for row in type_result.all()}

        # Aggregate results
        runs = await self.get_completed(limit=100)
        total_passed = sum(r.passed or 0 for r in runs)
        total_failed = sum(r.failed or 0 for r in runs)
        total_skipped = sum(r.skipped or 0 for r in runs)

        return {
            "total_runs": total_runs,
            "by_status": by_status,
            "by_type": by_type,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "period_days": days,
        }
