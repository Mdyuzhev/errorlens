"""Test plan service - business logic layer."""

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TestPlan, TestPlanRun
from app.repositories.test_plan_repo import TestPlanRepository
from app.services import event_publisher
from app.services.project_service import ProjectService

VALID_STATUSES = ["draft", "active", "archived"]
VALID_RESULT_STATUSES = ["passed", "failed", "blocked", "skipped"]


class TestPlanService:
    """Service for test plan business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TestPlanRepository(db)

    async def create_plan(
        self,
        name: str,
        project_id: str,
        description: str | None = None,
        status: str = "draft",
        created_by: str | None = None,
    ) -> TestPlan:
        """Create a new test plan."""
        if status not in VALID_STATUSES:
            status = "draft"

        plan_data: dict[str, Any] = {
            "name": name,
            "description": description,
            "status": status,
            "project_id": project_id,
            "created_by": created_by,
            "created_at": datetime.utcnow(),
        }

        # Generate human_id
        project_service = ProjectService(self.db)
        human_id = await project_service.next_human_id(project_id)
        if human_id:
            plan_data["human_id"] = human_id

        plan = await self.repo.create(plan_data)
        await self.db.commit()
        return plan

    async def get_plan(self, plan_id: str) -> TestPlan | None:
        """Get plan by ID."""
        return await self.repo.get_by_id(plan_id)

    async def get_plan_detail(self, plan_id: str) -> dict[str, Any] | None:
        """Get plan with cases."""
        plan = await self.repo.get_with_cases(plan_id)
        if not plan:
            return None

        cases = []
        for pc in sorted(plan.cases, key=lambda c: c.sort_order):
            tc = pc.testcase
            if tc:
                cases.append({
                    "testcase_id": tc.id,
                    "sort_order": pc.sort_order,
                    "title": tc.title,
                    "priority": tc.priority,
                    "status": tc.status,
                    "human_id": tc.human_id,
                })

        return {
            "id": plan.id,
            "human_id": plan.human_id,
            "name": plan.name,
            "description": plan.description,
            "status": plan.status,
            "project_id": plan.project_id,
            "created_by": plan.created_by,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "cases": cases,
            "cases_count": len(cases),
        }

    async def list_plans(self, project_id: str) -> list[dict[str, Any]]:
        """List plans for a project with summary stats."""
        plans = await self.repo.list_by_project(project_id)
        result = []
        for plan in plans:
            cases_count = await self.repo.cases_count(plan.id)
            runs_count = await self.repo.runs_count(plan.id)

            # Get last run info
            runs = await self.repo.list_runs(plan.id)
            last_run_at = None
            last_run_passed_pct = None
            if runs:
                last_run = runs[0]
                last_run_at = last_run.started_at.isoformat() if last_run.started_at else None
                if last_run.total > 0:
                    last_run_passed_pct = round(last_run.passed / last_run.total * 100)

            result.append({
                "id": plan.id,
                "human_id": plan.human_id,
                "name": plan.name,
                "status": plan.status,
                "cases_count": cases_count,
                "runs_count": runs_count,
                "last_run_at": last_run_at,
                "last_run_passed_pct": last_run_passed_pct,
                "created_at": plan.created_at.isoformat() if plan.created_at else None,
            })
        return result

    async def update_plan(self, plan_id: str, **updates: Any) -> TestPlan | None:
        """Update plan fields."""
        plan = await self.repo.get_by_id(plan_id)
        if not plan:
            return None

        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")

        for key, value in updates.items():
            if value is not None:
                setattr(plan, key, value)

        plan.updated_at = datetime.utcnow()
        await self.db.commit()
        return plan

    async def delete_plan(self, plan_id: str) -> bool:
        """Delete plan."""
        deleted = await self.repo.delete(plan_id)
        if deleted:
            await self.db.commit()
        return deleted

    # --- Cases ---

    async def add_cases_to_plan(
        self, plan_id: str, testcase_ids: list[str]
    ) -> None:
        """Add multiple test cases to plan."""
        plan = await self.repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        current_count = await self.repo.cases_count(plan_id)
        for idx, tc_id in enumerate(testcase_ids):
            if await self.repo.case_exists(plan_id, tc_id):
                raise HTTPException(
                    status_code=400,
                    detail="Test case already in plan",
                )
            await self.repo.add_case(plan_id, tc_id, sort_order=current_count + idx)

        await self.db.commit()

    async def remove_case(self, plan_id: str, testcase_id: str) -> bool:
        """Remove a case from plan."""
        removed = await self.repo.remove_case(plan_id, testcase_id)
        if removed:
            await self.db.commit()
        return removed

    async def reorder_cases(self, plan_id: str, ordered_ids: list[str]) -> bool:
        """Reorder cases in plan."""
        result = await self.repo.reorder_cases(plan_id, ordered_ids)
        await self.db.commit()
        return result

    # --- Runs ---

    async def start_run(
        self,
        plan_id: str,
        name: str,
        started_by: str | None = None,
    ) -> TestPlanRun:
        """Start a new run for a plan."""
        plan = await self.repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        if plan.status == "archived":
            raise HTTPException(status_code=400, detail="Cannot run archived plan")

        total = await self.repo.cases_count(plan_id)

        run = await self.repo.create_run({
            "plan_id": plan_id,
            "name": name,
            "started_by": started_by,
            "started_at": datetime.utcnow(),
            "total": total,
        })
        await self.db.commit()

        await event_publisher.publish(
            "testplan_run.started",
            {"run_id": run.id, "plan_id": plan_id, "plan_name": plan.name, "total": total},
            project_id=plan.project_id,
        )

        return run

    async def record_result(
        self,
        run_id: str,
        testcase_id: str,
        status: str,
        comment: str | None = None,
        error_details: str | None = None,
        executed_by: str | None = None,
    ) -> dict[str, Any]:
        """Record or update a result for a testcase in a run."""
        run = await self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status == "completed":
            raise HTTPException(status_code=400, detail="Run is already completed")
        if status not in VALID_RESULT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid result status")

        result = await self.repo.upsert_result(run_id, testcase_id, {
            "status": status,
            "comment": comment,
            "error_details": error_details,
            "executed_by": executed_by,
        })

        # Recalculate counters from DB
        counts = await self.repo.count_results_by_status(run_id)
        run.passed = counts["passed"]
        run.failed = counts["failed"]
        run.blocked = counts["blocked"]
        run.skipped = counts["skipped"]
        await self.db.commit()

        await event_publisher.publish(
            "testplan_run.result_recorded",
            {"run_id": run_id, "testcase_id": testcase_id, "status": status},
            project_id=run.plan.project_id if run.plan else None,
        )

        return {
            "id": result.id,
            "run_id": result.run_id,
            "testcase_id": result.testcase_id,
            "status": result.status,
            "comment": result.comment,
            "error_details": result.error_details,
            "executed_at": result.executed_at.isoformat() if result.executed_at else None,
            "executed_by": result.executed_by,
            "counters": counts,
        }

    async def finish_run(self, run_id: str) -> TestPlanRun:
        """Finish a run."""
        run = await self.repo.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status == "completed":
            raise HTTPException(status_code=400, detail="Run is already completed")

        results_count = await self.repo.results_count(run_id)
        if results_count == 0:
            raise HTTPException(status_code=400, detail="Cannot finish empty run")

        counts = await self.repo.count_results_by_status(run_id)
        finished = await self.repo.finish_run(run_id, counts)
        await self.db.commit()

        plan = await self.repo.get_by_id(run.plan_id)
        await event_publisher.publish(
            "testplan_run.completed",
            {
                "run_id": run_id, "plan_id": run.plan_id,
                "plan_name": plan.name if plan else "",
                "total": finished.total, "passed": finished.passed,
                "failed": finished.failed, "blocked": finished.blocked,
            },
            project_id=plan.project_id if plan else None,
        )

        return finished

    async def get_run_detail(self, run_id: str) -> dict[str, Any] | None:
        """Get run with all results and testcase info.

        Returns ALL plan cases, merging with recorded results.
        Cases without results have status=None.
        """
        run = await self.repo.get_run(run_id)
        if not run:
            return None

        results = await self.repo.get_results(run_id)

        # Get plan with all cases
        plan = await self.repo.get_with_cases(run.plan_id)
        plan_name = plan.name if plan else None

        # Build results map by testcase_id
        results_map: dict[str, Any] = {}
        for r in results:
            results_map[r.testcase_id] = r

        # Build list from ALL plan cases, merging with results
        results_list = []
        if plan:
            for pc in sorted(plan.cases, key=lambda c: c.sort_order):
                tc = pc.testcase
                if not tc:
                    continue
                r = results_map.get(tc.id)
                results_list.append({
                    "testcase_id": tc.id,
                    "title": tc.title,
                    "priority": tc.priority,
                    "steps": tc.steps,
                    "human_id": tc.human_id,
                    "status": r.status if r else None,
                    "comment": r.comment if r else None,
                    "error_details": r.error_details if r else None,
                    "executed_at": r.executed_at.isoformat() if r and r.executed_at else None,
                })

        return {
            "id": run.id,
            "plan_id": run.plan_id,
            "plan_name": plan_name,
            "name": run.name,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "total": run.total,
            "passed": run.passed,
            "failed": run.failed,
            "blocked": run.blocked,
            "skipped": run.skipped,
            "results": results_list,
        }

    def run_to_summary(self, run: TestPlanRun) -> dict[str, Any]:
        """Convert run to summary dict."""
        return {
            "id": run.id,
            "name": run.name,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "total": run.total,
            "passed": run.passed,
            "failed": run.failed,
            "blocked": run.blocked,
            "skipped": run.skipped,
        }
