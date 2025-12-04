"""Test runs API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.db_models import TestRun
from app.models.user import User

router = APIRouter(prefix="/test-runs", tags=["test-runs"])


@router.get("")
async def list_test_runs(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get recent test runs."""
    result = await db.execute(
        select(TestRun).order_by(TestRun.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()

    return [
        {
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
            "results": run.results,
        }
        for run in runs
    ]


@router.get("/stats/summary")
async def get_test_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get aggregated test statistics."""
    # Last 5 completed runs
    result = await db.execute(
        select(TestRun)
        .where(TestRun.status.in_(["passed", "failed"]))
        .order_by(TestRun.started_at.desc())
        .limit(5)
    )
    runs = result.scalars().all()

    total_passed = sum(r.passed for r in runs)
    total_failed = sum(r.failed for r in runs)
    total_skipped = sum(r.skipped for r in runs)
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


@router.get("/{run_id}")
async def get_test_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test run details with steps."""
    result = await db.execute(select(TestRun).where(TestRun.id == run_id))
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

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
        "results": run.results,
        "output": run.output,
    }
