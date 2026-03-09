"""Tests for test plan service business logic."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.test_plan_service import TestPlanService, VALID_RESULT_STATUSES


def _make_plan(**overrides):
    """Create a mock TestPlan."""
    plan = MagicMock()
    plan.id = overrides.get("id", "plan-1")
    plan.human_id = overrides.get("human_id", "EL-1")
    plan.name = overrides.get("name", "Test Plan")
    plan.description = overrides.get("description", None)
    plan.status = overrides.get("status", "active")
    plan.project_id = overrides.get("project_id", "proj-1")
    plan.created_by = overrides.get("created_by", "user-1")
    plan.created_at = overrides.get("created_at", datetime(2026, 3, 9))
    plan.updated_at = overrides.get("updated_at", None)
    plan.cases = overrides.get("cases", [])
    return plan


def _make_run(**overrides):
    """Create a mock TestPlanRun."""
    run = MagicMock()
    run.id = overrides.get("id", "run-1")
    run.plan_id = overrides.get("plan_id", "plan-1")
    run.name = overrides.get("name", "Run 1")
    run.status = overrides.get("status", "in_progress")
    run.started_by = overrides.get("started_by", "user-1")
    run.started_at = overrides.get("started_at", datetime(2026, 3, 9))
    run.finished_at = overrides.get("finished_at", None)
    run.total = overrides.get("total", 5)
    run.passed = overrides.get("passed", 0)
    run.failed = overrides.get("failed", 0)
    run.blocked = overrides.get("blocked", 0)
    run.skipped = overrides.get("skipped", 0)
    return run


def _make_result(**overrides):
    """Create a mock TestPlanRunResult."""
    result = MagicMock()
    result.id = overrides.get("id", "res-1")
    result.run_id = overrides.get("run_id", "run-1")
    result.testcase_id = overrides.get("testcase_id", "tc-1")
    result.status = overrides.get("status", "passed")
    result.comment = overrides.get("comment", None)
    result.error_details = overrides.get("error_details", None)
    result.executed_at = overrides.get("executed_at", datetime(2026, 3, 9, 10))
    result.executed_by = overrides.get("executed_by", "user-1")
    return result


def _make_service():
    """Create TestPlanService with mocked DB."""
    db = AsyncMock()
    db.commit = AsyncMock()
    service = TestPlanService(db)
    service.repo = MagicMock()
    # Make all repo methods async
    service.repo.create = AsyncMock()
    service.repo.get_by_id = AsyncMock()
    service.repo.get_with_cases = AsyncMock()
    service.repo.list_by_project = AsyncMock()
    service.repo.delete = AsyncMock()
    service.repo.add_case = AsyncMock()
    service.repo.remove_case = AsyncMock()
    service.repo.case_exists = AsyncMock()
    service.repo.cases_count = AsyncMock()
    service.repo.reorder_cases = AsyncMock()
    service.repo.create_run = AsyncMock()
    service.repo.get_run = AsyncMock()
    service.repo.list_runs = AsyncMock()
    service.repo.runs_count = AsyncMock()
    service.repo.upsert_result = AsyncMock()
    service.repo.get_results = AsyncMock()
    service.repo.count_results_by_status = AsyncMock()
    service.repo.results_count = AsyncMock()
    service.repo.finish_run = AsyncMock()
    return service


class TestCreatePlan:
    """Tests for plan creation."""

    @pytest.mark.asyncio
    async def test_create_plan(self):
        """Plan created, human_id assigned."""
        service = _make_service()
        plan = _make_plan()
        service.repo.create.return_value = plan

        with patch("app.services.test_plan_service.ProjectService") as MockPS:
            mock_ps = AsyncMock()
            mock_ps.next_human_id.return_value = "EL-1"
            MockPS.return_value = mock_ps

            result = await service.create_plan(
                name="Test Plan",
                project_id="proj-1",
                created_by="user-1",
            )

        assert result == plan
        service.repo.create.assert_awaited_once()
        call_data = service.repo.create.call_args[0][0]
        assert call_data["human_id"] == "EL-1"
        assert call_data["name"] == "Test Plan"

    @pytest.mark.asyncio
    async def test_create_plan_invalid_status_defaults_draft(self):
        """Invalid status falls back to draft."""
        service = _make_service()
        service.repo.create.return_value = _make_plan(status="draft")

        with patch("app.services.test_plan_service.ProjectService") as MockPS:
            mock_ps = AsyncMock()
            mock_ps.next_human_id.return_value = "EL-2"
            MockPS.return_value = mock_ps

            await service.create_plan(
                name="Plan", project_id="p1", status="invalid"
            )

        call_data = service.repo.create.call_args[0][0]
        assert call_data["status"] == "draft"


class TestAddCases:
    """Tests for adding cases to plan."""

    @pytest.mark.asyncio
    async def test_add_cases(self):
        """Cases added successfully."""
        service = _make_service()
        service.repo.get_by_id.return_value = _make_plan()
        service.repo.case_exists.return_value = False
        service.repo.cases_count.return_value = 0

        await service.add_cases_to_plan("plan-1", ["tc-1", "tc-2"])

        assert service.repo.add_case.await_count == 2

    @pytest.mark.asyncio
    async def test_add_duplicate_case_raises_400(self):
        """Duplicate case raises 400."""
        service = _make_service()
        service.repo.get_by_id.return_value = _make_plan()
        service.repo.case_exists.return_value = True
        service.repo.cases_count.return_value = 1

        with pytest.raises(HTTPException) as exc:
            await service.add_cases_to_plan("plan-1", ["tc-1"])

        assert exc.value.status_code == 400
        assert "already in plan" in exc.value.detail


class TestStartRun:
    """Tests for starting a run."""

    @pytest.mark.asyncio
    async def test_start_run(self):
        """Run created with status in_progress, total = N."""
        service = _make_service()
        plan = _make_plan(status="active")
        service.repo.get_by_id.return_value = plan
        service.repo.cases_count.return_value = 5
        run = _make_run(total=5)
        service.repo.create_run.return_value = run

        result = await service.start_run("plan-1", "Run 1", started_by="user-1")

        assert result == run
        call_data = service.repo.create_run.call_args[0][0]
        assert call_data["total"] == 5

    @pytest.mark.asyncio
    async def test_run_archived_plan_raises_400(self):
        """Cannot run archived plan → 400."""
        service = _make_service()
        service.repo.get_by_id.return_value = _make_plan(status="archived")

        with pytest.raises(HTTPException) as exc:
            await service.start_run("plan-1", "Run 1")

        assert exc.value.status_code == 400
        assert "archived" in exc.value.detail.lower()


class TestRecordResult:
    """Tests for recording results."""

    @pytest.mark.asyncio
    async def test_record_result_pass(self):
        """Record passed result, counters updated."""
        service = _make_service()
        run = _make_run()
        service.repo.get_run.return_value = run
        result = _make_result(status="passed")
        service.repo.upsert_result.return_value = result
        service.repo.count_results_by_status.return_value = {
            "passed": 1, "failed": 0, "blocked": 0, "skipped": 0,
        }

        resp = await service.record_result("run-1", "tc-1", "passed")

        assert resp["status"] == "passed"
        assert resp["counters"]["passed"] == 1
        assert run.passed == 1

    @pytest.mark.asyncio
    async def test_record_result_rewrite_counters_recalculated(self):
        """Re-mark case → counters recalculated correctly."""
        service = _make_service()
        run = _make_run(passed=1)
        service.repo.get_run.return_value = run
        result = _make_result(status="failed")
        service.repo.upsert_result.return_value = result
        # After re-mark: was passed, now failed
        service.repo.count_results_by_status.return_value = {
            "passed": 0, "failed": 1, "blocked": 0, "skipped": 0,
        }

        resp = await service.record_result("run-1", "tc-1", "failed")

        assert resp["counters"]["passed"] == 0
        assert resp["counters"]["failed"] == 1
        assert run.passed == 0
        assert run.failed == 1

    @pytest.mark.asyncio
    async def test_record_in_completed_run_raises_400(self):
        """Cannot record in completed run → 400."""
        service = _make_service()
        service.repo.get_run.return_value = _make_run(status="completed")

        with pytest.raises(HTTPException) as exc:
            await service.record_result("run-1", "tc-1", "passed")

        assert exc.value.status_code == 400
        assert "completed" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_record_invalid_status_raises_400(self):
        """Invalid result status → 400."""
        service = _make_service()
        service.repo.get_run.return_value = _make_run()

        with pytest.raises(HTTPException) as exc:
            await service.record_result("run-1", "tc-1", "invalid_status")

        assert exc.value.status_code == 400


class TestFinishRun:
    """Tests for finishing a run."""

    @pytest.mark.asyncio
    async def test_finish_run(self):
        """Run finished, status completed, finished_at set."""
        service = _make_service()
        run = _make_run()
        service.repo.get_run.return_value = run
        service.repo.results_count.return_value = 3
        service.repo.count_results_by_status.return_value = {
            "passed": 2, "failed": 1, "blocked": 0, "skipped": 0,
        }
        finished_run = _make_run(
            status="completed",
            finished_at=datetime(2026, 3, 9, 12),
        )
        service.repo.finish_run.return_value = finished_run

        result = await service.finish_run("run-1")

        assert result.status == "completed"
        assert result.finished_at is not None

    @pytest.mark.asyncio
    async def test_finish_empty_run_raises_400(self):
        """Cannot finish run with 0 results → 400."""
        service = _make_service()
        service.repo.get_run.return_value = _make_run()
        service.repo.results_count.return_value = 0

        with pytest.raises(HTTPException) as exc:
            await service.finish_run("run-1")

        assert exc.value.status_code == 400
        assert "empty" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_finish_completed_run_raises_400(self):
        """Cannot finish already completed run → 400."""
        service = _make_service()
        service.repo.get_run.return_value = _make_run(status="completed")

        with pytest.raises(HTTPException) as exc:
            await service.finish_run("run-1")

        assert exc.value.status_code == 400


class TestGetRunWithResults:
    """Tests for get_run_detail."""

    @pytest.mark.asyncio
    async def test_get_run_with_results(self):
        """All cases included, not just marked ones."""
        service = _make_service()
        run = _make_run(total=3, passed=1)
        service.repo.get_run.return_value = run

        # Mock plan with cases (get_with_cases returns plan with .cases)
        tc1 = MagicMock()
        tc1.id = "tc-1"
        tc1.title = "TC 1"
        tc1.priority = "High"
        tc1.steps = []
        tc1.human_id = "EL-1"

        tc2 = MagicMock()
        tc2.id = "tc-2"
        tc2.title = "TC 2"
        tc2.priority = "Medium"
        tc2.steps = []
        tc2.human_id = "EL-2"

        pc1 = MagicMock()
        pc1.sort_order = 0
        pc1.testcase = tc1

        pc2 = MagicMock()
        pc2.sort_order = 1
        pc2.testcase = tc2

        plan = _make_plan(cases=[pc1, pc2])
        service.repo.get_with_cases.return_value = plan

        # Only tc-1 has a recorded result
        r1 = _make_result(testcase_id="tc-1", status="passed")
        r1.testcase = tc1
        service.repo.get_results.return_value = [r1]

        detail = await service.get_run_detail("run-1")

        assert detail is not None
        assert len(detail["results"]) == 2
        assert detail["results"][0]["status"] == "passed"
        assert detail["plan_name"] == "Test Plan"

    @pytest.mark.asyncio
    async def test_get_run_not_found(self):
        """Non-existent run returns None."""
        service = _make_service()
        service.repo.get_run.return_value = None

        result = await service.get_run_detail("nonexistent")

        assert result is None


class TestRunToSummary:
    """Tests for run_to_summary helper."""

    def test_run_to_summary_fields(self):
        """Summary contains all required fields."""
        service = _make_service()
        run = _make_run(
            passed=3, failed=1, blocked=1, skipped=0, total=5,
        )

        summary = service.run_to_summary(run)

        assert summary["id"] == "run-1"
        assert summary["total"] == 5
        assert summary["passed"] == 3
        assert summary["failed"] == 1
        assert summary["status"] == "in_progress"
