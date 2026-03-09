"""Test plan repository - data access layer."""

from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import (
    TestPlan,
    TestPlanCase,
    TestPlanRun,
    TestPlanRunResult,
)
from app.repositories.base import BaseRepository


class TestPlanRepository(BaseRepository[TestPlan]):
    """Repository for TestPlan CRUD operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(TestPlan, db)

    async def list_by_project(self, project_id: str) -> list[TestPlan]:
        """Get all plans for a project with case/run counts."""
        query = (
            select(TestPlan)
            .where(TestPlan.project_id == project_id)
            .order_by(TestPlan.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_cases(self, plan_id: str) -> TestPlan | None:
        """Get plan with cases eagerly loaded."""
        query = (
            select(TestPlan)
            .where(TestPlan.id == plan_id)
            .options(
                selectinload(TestPlan.cases).selectinload(TestPlanCase.testcase)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def add_case(
        self, plan_id: str, testcase_id: str, sort_order: int = 0
    ) -> TestPlanCase:
        """Add a test case to plan."""
        link = TestPlanCase(
            plan_id=plan_id,
            testcase_id=testcase_id,
            sort_order=sort_order,
        )
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)
        return link

    async def remove_case(self, plan_id: str, testcase_id: str) -> bool:
        """Remove a test case from plan."""
        stmt = delete(TestPlanCase).where(
            TestPlanCase.plan_id == plan_id,
            TestPlanCase.testcase_id == testcase_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def get_cases(self, plan_id: str) -> list[TestPlanCase]:
        """Get plan cases with joined testcase data."""
        query = (
            select(TestPlanCase)
            .where(TestPlanCase.plan_id == plan_id)
            .options(selectinload(TestPlanCase.testcase))
            .order_by(TestPlanCase.sort_order)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def case_exists(self, plan_id: str, testcase_id: str) -> bool:
        """Check if testcase is already in plan."""
        query = select(func.count()).select_from(TestPlanCase).where(
            TestPlanCase.plan_id == plan_id,
            TestPlanCase.testcase_id == testcase_id,
        )
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    async def cases_count(self, plan_id: str) -> int:
        """Count cases in plan."""
        query = select(func.count()).select_from(TestPlanCase).where(
            TestPlanCase.plan_id == plan_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def reorder_cases(self, plan_id: str, ordered_ids: list[str]) -> bool:
        """Reorder cases in plan by list of testcase IDs."""
        for idx, tc_id in enumerate(ordered_ids):
            stmt = (
                update(TestPlanCase)
                .where(
                    TestPlanCase.plan_id == plan_id,
                    TestPlanCase.testcase_id == tc_id,
                )
                .values(sort_order=idx)
            )
            await self.session.execute(stmt)
        await self.session.flush()
        return True

    # --- Runs ---

    async def create_run(self, data: dict) -> TestPlanRun:
        """Create a new run."""
        run = TestPlanRun(**data)
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> TestPlanRun | None:
        """Get run by ID."""
        query = select(TestPlanRun).where(TestPlanRun.id == run_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_runs(self, plan_id: str) -> list[TestPlanRun]:
        """List all runs for a plan."""
        query = (
            select(TestPlanRun)
            .where(TestPlanRun.plan_id == plan_id)
            .order_by(TestPlanRun.started_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def runs_count(self, plan_id: str) -> int:
        """Count runs for a plan."""
        query = select(func.count()).select_from(TestPlanRun).where(
            TestPlanRun.plan_id == plan_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    # --- Results ---

    async def upsert_result(
        self, run_id: str, testcase_id: str, data: dict
    ) -> TestPlanRunResult:
        """Create or update a result for a testcase in a run."""
        query = select(TestPlanRunResult).where(
            TestPlanRunResult.run_id == run_id,
            TestPlanRunResult.testcase_id == testcase_id,
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.executed_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        record = TestPlanRunResult(
            run_id=run_id,
            testcase_id=testcase_id,
            executed_at=datetime.utcnow(),
            **data,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_results(self, run_id: str) -> list[TestPlanRunResult]:
        """Get all results for a run with testcase data."""
        query = (
            select(TestPlanRunResult)
            .where(TestPlanRunResult.run_id == run_id)
            .options(selectinload(TestPlanRunResult.testcase))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_results_by_status(self, run_id: str) -> dict[str, int]:
        """Count results grouped by status for a run."""
        query = (
            select(TestPlanRunResult.status, func.count())
            .where(TestPlanRunResult.run_id == run_id)
            .group_by(TestPlanRunResult.status)
        )
        result = await self.session.execute(query)
        counts = {"passed": 0, "failed": 0, "blocked": 0, "skipped": 0}
        for status, count in result.all():
            if status in counts:
                counts[status] = count
        return counts

    async def results_count(self, run_id: str) -> int:
        """Count total results in a run."""
        query = select(func.count()).select_from(TestPlanRunResult).where(
            TestPlanRunResult.run_id == run_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def finish_run(self, run_id: str, counts: dict[str, int]) -> TestPlanRun | None:
        """Mark run as completed with final counts."""
        run = await self.get_run(run_id)
        if not run:
            return None
        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.passed = counts.get("passed", 0)
        run.failed = counts.get("failed", 0)
        run.blocked = counts.get("blocked", 0)
        run.skipped = counts.get("skipped", 0)
        await self.session.flush()
        await self.session.refresh(run)
        return run
