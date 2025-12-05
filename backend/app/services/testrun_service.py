"""TestRun service - business logic layer."""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TestRun
from app.repositories.testrun_repo import TestRunRepository


VALID_STATUSES = ["pending", "running", "passed", "failed", "cancelled"]
VALID_TEST_TYPES = ["unit", "integration", "e2e", "api", "performance"]


class TestRunService:
    """Service for test run business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TestRunRepository(db)

    async def create_run(
        self,
        test_type: str,
        total_tests: int = 0,
        status: str = "pending",
    ) -> TestRun:
        """Create new test run."""
        if test_type not in VALID_TEST_TYPES:
            test_type = "unit"
        if status not in VALID_STATUSES:
            status = "pending"

        run_data = {
            "test_type": test_type,
            "status": status,
            "total_tests": total_tests,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "started_at": datetime.utcnow(),
        }

        run = await self.repo.create(run_data)
        await self.db.commit()
        return run

    async def get_run(self, run_id: str) -> Optional[TestRun]:
        """Get test run by ID."""
        return await self.repo.get_by_id(run_id)

    async def list_runs(
        self,
        limit: int = 10,
        offset: int = 0,
        test_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List test runs with filters."""
        runs = await self.repo.get_recent(
            limit=limit,
            offset=offset,
            test_type=test_type,
            status=status,
        )
        return [self._to_list_dict(r) for r in runs]

    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get aggregated test statistics from recent runs."""
        runs = await self.repo.get_completed(limit=5)

        total_passed = sum(r.passed or 0 for r in runs)
        total_failed = sum(r.failed or 0 for r in runs)
        total_skipped = sum(r.skipped or 0 for r in runs)
        total_tests = total_passed + total_failed + total_skipped

        return {
            "total_runs": len(runs),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "pass_rate": round(total_passed / total_tests * 100, 1) if total_tests > 0 else 0,
            "runs": [
                {
                    "id": r.id,
                    "date": r.started_at.strftime("%Y-%m-%d") if r.started_at else None,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                }
                for r in runs
            ],
        }

    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get detailed statistics."""
        return await self.repo.get_stats(days=days)

    async def update_run(
        self,
        run_id: str,
        **updates
    ) -> Optional[TestRun]:
        """Update test run fields."""
        run = await self.repo.get_by_id(run_id)
        if not run:
            return None

        for key, value in updates.items():
            if value is not None:
                setattr(run, key, value)

        await self.db.commit()
        return run

    async def finish_run(
        self,
        run_id: str,
        status: str,
        passed: int,
        failed: int,
        skipped: int,
        results: Optional[List[dict]] = None,
        output: Optional[str] = None,
    ) -> Optional[TestRun]:
        """Finish test run with results."""
        run = await self.repo.get_by_id(run_id)
        if not run:
            return None

        run.status = status if status in VALID_STATUSES else "failed"
        run.passed = passed
        run.failed = failed
        run.skipped = skipped
        run.total_tests = passed + failed + skipped
        run.finished_at = datetime.utcnow()
        run.results = results
        run.output = output

        if run.started_at:
            run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

        await self.db.commit()
        return run

    async def cancel_run(self, run_id: str) -> Optional[TestRun]:
        """Cancel a running test."""
        run = await self.repo.get_by_id(run_id)
        if not run:
            return None

        if run.status in ["pending", "running"]:
            run.status = "cancelled"
            run.finished_at = datetime.utcnow()
            await self.db.commit()

        return run

    async def delete_run(self, run_id: str) -> bool:
        """Delete test run."""
        deleted = await self.repo.delete(run_id)
        if deleted:
            await self.db.commit()
        return deleted

    def _to_list_dict(self, run: TestRun) -> Dict[str, Any]:
        """Convert test run to list response dict."""
        return {
            "id": run.id,
            "test_type": run.test_type,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "duration_ms": run.duration_ms,
            "total_tests": run.total_tests,
            "passed": run.passed,
            "failed": run.failed,
            "skipped": run.skipped,
        }

    def to_detail_dict(self, run: TestRun) -> Dict[str, Any]:
        """Convert test run to detailed response dict."""
        result = self._to_list_dict(run)
        result["results"] = run.results
        result["output"] = run.output
        return result
