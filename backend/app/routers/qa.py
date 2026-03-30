"""QA dashboard router."""

import json
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.task import SprintIssue, Task, TaskType
from app.models.testcase import TestCase, TestCaseFolder
from app.models.testplan import TestPlan, TestPlanRun, TestPlanRunResult
from app.models.user import User
from app.services.redis_client import get_redis

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])

CACHE_TTL = 300
COVERAGE_CACHE_TTL = 60


@router.get("/dashboard")
async def get_qa_dashboard(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """QA dashboard with Redis cache."""
    cache_key = f"qa:dashboard:{project_id}"
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return JSONResponse(content=json.loads(cached), headers={"X-Cache": "HIT"})
    except Exception:
        pass

    result = await db.execute(
        select(TestCase.status, func.count(TestCase.id).label("count"))
        .where(TestCase.project_id == project_id)
        .group_by(TestCase.status)
    )
    by_status = [{"status": r.status, "count": r.count} for r in result.all()]

    result2 = await db.execute(
        select(TestCase.id, TestCase.title, func.count(TestPlanRunResult.id).label("failed_count"))
        .join(TestPlanRunResult, TestPlanRunResult.testcase_id == TestCase.id)
        .where(TestCase.project_id == project_id, TestPlanRunResult.status == "failed")
        .group_by(TestCase.id, TestCase.title)
        .order_by(func.count(TestPlanRunResult.id).desc())
        .limit(5)
    )
    top_failed = [{"id": r.id, "title": r.title, "failed_count": r.failed_count} for r in result2.all()]

    # --- trend: last 10 runs for project ---
    runs_q = (
        select(TestPlanRun)
        .join(TestPlan, TestPlan.id == TestPlanRun.plan_id)
        .where(TestPlan.project_id == project_id)
        .order_by(TestPlanRun.started_at.desc())
        .limit(10)
    )
    runs_result = await db.execute(runs_q)
    runs = list(reversed(runs_result.scalars().all()))

    trend = []
    for run in runs:
        counts_q = (
            select(TestPlanRunResult.status, func.count(TestPlanRunResult.id).label("cnt"))
            .where(TestPlanRunResult.run_id == run.id)
            .group_by(TestPlanRunResult.status)
        )
        counts_result = await db.execute(counts_q)
        counts = {r.status: r.cnt for r in counts_result.all()}
        trend.append({
            "date": run.started_at.strftime("%d.%m") if run.started_at else "",
            "label": run.name[:20] if run.name else "",
            "passed": counts.get("passed", 0),
            "failed": counts.get("failed", 0) + counts.get("blocked", 0),
        })

    # --- coverage: % covered cases per folder ---
    folders_q = select(TestCaseFolder).where(TestCaseFolder.project_id == project_id)
    folders_result = await db.execute(folders_q)
    folders = folders_result.scalars().all()

    coverage = {}
    for folder in folders:
        total_q = select(func.count(TestCase.id)).where(
            TestCase.folder_id == folder.id,
            TestCase.project_id == project_id,
        )
        total_res = await db.execute(total_q)
        total = total_res.scalar() or 0
        if total == 0:
            continue

        covered_q = (
            select(func.count(TestPlanRunResult.testcase_id.distinct()))
            .join(TestCase, TestCase.id == TestPlanRunResult.testcase_id)
            .where(
                TestCase.folder_id == folder.id,
                TestCase.project_id == project_id,
                TestPlanRunResult.status == "passed",
            )
        )
        covered_res = await db.execute(covered_q)
        covered = covered_res.scalar() or 0
        coverage[folder.name] = round(covered / total * 100)

    if not coverage:
        total_q = select(func.count(TestCase.id)).where(TestCase.project_id == project_id)
        total_res = await db.execute(total_q)
        total = total_res.scalar() or 0
        if total > 0:
            covered_q = (
                select(func.count(TestPlanRunResult.testcase_id.distinct()))
                .join(TestCase, TestCase.id == TestPlanRunResult.testcase_id)
                .where(
                    TestCase.project_id == project_id,
                    TestPlanRunResult.status == "passed",
                )
            )
            covered_res = await db.execute(covered_q)
            covered = covered_res.scalar() or 0
            coverage["All"] = round(covered / total * 100)

    data = {"by_status": by_status, "top_failed": top_failed, "trend": trend, "coverage": coverage}

    try:
        redis = await get_redis()
        await redis.setex(cache_key, CACHE_TTL, json.dumps(data))
    except Exception:
        pass

    return JSONResponse(content=data, headers={"X-Cache": "MISS"})


def _coverage_status(tc_nodes: list[dict]) -> str:
    """Determine coverage status for an issue based on its test cases."""
    if not tc_nodes:
        return "none"
    statuses = [tc.get("last_run_status") for tc in tc_nodes]
    if all(s is None for s in statuses):
        return "not_run"
    if all(s == "passed" for s in statuses if s is not None):
        if any(s is None for s in statuses):
            return "partial"
        return "passing"
    if any(s == "failed" for s in statuses):
        return "failing"
    return "partial"


@router.get("/coverage")
async def get_qa_coverage(
    project_id: str = Query(...),
    sprint_id: str | None = Query(None),
    type_slug: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Coverage view: issues with linked test cases and run results."""
    cache_key = f"qa:coverage:{project_id}:{sprint_id}:{type_slug}"
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return JSONResponse(content=json.loads(cached), headers={"X-Cache": "HIT"})
    except Exception:
        pass

    # 1. Build issue query with optional filters
    issue_q = (
        select(Task)
        .where(Task.project_id == project_id)
        .options(selectinload(Task.task_type), selectinload(Task.task_status))
    )

    if sprint_id:
        issue_q = issue_q.join(SprintIssue, SprintIssue.issue_id == Task.id).where(
            SprintIssue.sprint_id == sprint_id
        )

    if type_slug:
        issue_q = issue_q.join(TaskType, TaskType.id == Task.type_id).where(
            TaskType.slug == type_slug
        )

    result = await db.execute(issue_q)
    issues = result.scalars().all()

    if not issues:
        data = {"issues": [], "summary": {
            "total_issues": 0, "covered_issues": 0, "coverage_pct": 0,
            "total_test_cases": 0, "passed": 0, "failed": 0, "not_run": 0,
        }}
        try:
            redis = await get_redis()
            await redis.setex(cache_key, COVERAGE_CACHE_TTL, json.dumps(data))
        except Exception:
            pass
        return JSONResponse(content=data, headers={"X-Cache": "MISS"})

    issue_ids = [i.id for i in issues]

    # 2. Find test cases linked to these issues via JSON linked_issue_ids
    tc_q = select(TestCase).where(TestCase.project_id == project_id)
    result_tc = await db.execute(tc_q)
    all_test_cases = result_tc.scalars().all()

    # Build mapping: issue_id -> list of test cases
    issue_tc_map: dict[str, list] = defaultdict(list)
    tc_ids_set: set[str] = set()
    for tc in all_test_cases:
        linked = tc.linked_issue_ids
        if not linked or not isinstance(linked, list):
            continue
        for tid in issue_ids:
            if tid in linked:
                issue_tc_map[tid].append(tc)
                tc_ids_set.add(tc.id)

    # 3. Find last run result for each test case
    tc_last_run: dict[str, str | None] = {}
    if tc_ids_set:
        # Subquery: max executed_at per testcase_id
        latest_sq = (
            select(
                TestPlanRunResult.testcase_id,
                func.max(TestPlanRunResult.executed_at).label("max_exec"),
            )
            .where(TestPlanRunResult.testcase_id.in_(list(tc_ids_set)))
            .group_by(TestPlanRunResult.testcase_id)
            .subquery()
        )
        run_q = (
            select(TestPlanRunResult.testcase_id, TestPlanRunResult.status)
            .join(
                latest_sq,
                and_(
                    TestPlanRunResult.testcase_id == latest_sq.c.testcase_id,
                    TestPlanRunResult.executed_at == latest_sq.c.max_exec,
                ),
            )
        )
        run_result = await db.execute(run_q)
        for row in run_result.all():
            tc_last_run[row.testcase_id] = row.status

    # 4. Build response
    summary_passed = 0
    summary_failed = 0
    summary_not_run = 0
    covered_issues = 0
    total_tc = len(tc_ids_set)

    issue_nodes = []
    for issue in issues:
        tcs = issue_tc_map.get(issue.id, [])
        tc_nodes = []
        for tc in tcs:
            last_status = tc_last_run.get(tc.id)
            tc_nodes.append({
                "id": tc.id,
                "human_id": tc.human_id,
                "title": tc.title,
                "priority": tc.priority,
                "status": tc.status,
                "last_run_status": last_status,
            })
            if last_status == "passed":
                summary_passed += 1
            elif last_status == "failed":
                summary_failed += 1
            else:
                summary_not_run += 1

        has_tests = len(tc_nodes) > 0
        if has_tests:
            covered_issues += 1

        cov_status = _coverage_status(tc_nodes)

        type_name = issue.task_type.name if issue.task_type else None
        status_name = issue.task_status.name if issue.task_status else issue.status

        issue_nodes.append({
            "id": issue.id,
            "human_id": issue.human_id,
            "title": issue.title,
            "priority": issue.priority,
            "type": type_name,
            "status": status_name,
            "has_tests": has_tests,
            "test_cases": tc_nodes,
            "coverage_status": cov_status,
        })

    total_issues = len(issues)
    coverage_pct = round(covered_issues / total_issues * 100) if total_issues > 0 else 0

    data = {
        "issues": issue_nodes,
        "summary": {
            "total_issues": total_issues,
            "covered_issues": covered_issues,
            "coverage_pct": coverage_pct,
            "total_test_cases": total_tc,
            "passed": summary_passed,
            "failed": summary_failed,
            "not_run": summary_not_run,
        },
    }

    try:
        redis = await get_redis()
        await redis.setex(cache_key, COVERAGE_CACHE_TTL, json.dumps(data))
    except Exception:
        pass

    return JSONResponse(content=data, headers={"X-Cache": "MISS"})
