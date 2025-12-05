"""Test runs API router - thin controller."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.testrun_service import TestRunService


router = APIRouter(prefix="/test-runs", tags=["test-runs"])


class TestRunCreate(BaseModel):
    test_type: str
    total_tests: int = 0


class TestRunFinish(BaseModel):
    status: str
    passed: int
    failed: int
    skipped: int
    results: Optional[List[dict]] = None
    output: Optional[str] = None


@router.get("")
async def list_test_runs(
    limit: int = 10,
    offset: int = 0,
    test_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test runs with filters."""
    service = TestRunService(db)
    return await service.list_runs(
        limit=limit,
        offset=offset,
        test_type=test_type,
        status=status,
    )


@router.get("/stats/summary")
async def get_summary_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get aggregated test statistics from recent runs."""
    service = TestRunService(db)
    return await service.get_summary_stats()


@router.get("/stats/detailed")
async def get_detailed_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get detailed statistics for the last N days."""
    service = TestRunService(db)
    return await service.get_stats(days=days)


@router.get("/{run_id}")
async def get_test_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get test run details."""
    service = TestRunService(db)
    run = await service.get_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

    return service.to_detail_dict(run)


@router.post("")
async def create_test_run(
    data: TestRunCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new test run."""
    service = TestRunService(db)
    run = await service.create_run(
        test_type=data.test_type,
        total_tests=data.total_tests,
    )
    return {"id": run.id, "message": "Test run created"}


@router.post("/{run_id}/finish")
async def finish_test_run(
    run_id: str,
    data: TestRunFinish,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Finish test run with results."""
    service = TestRunService(db)
    run = await service.finish_run(
        run_id=run_id,
        status=data.status,
        passed=data.passed,
        failed=data.failed,
        skipped=data.skipped,
        results=data.results,
        output=data.output,
    )

    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

    return {"message": "Test run finished", "duration_ms": run.duration_ms}


@router.post("/{run_id}/cancel")
async def cancel_test_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Cancel a running test."""
    service = TestRunService(db)
    run = await service.cancel_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail="Test run not found")

    return {"message": "Test run cancelled"}


@router.delete("/{run_id}")
async def delete_test_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete test run."""
    service = TestRunService(db)
    deleted = await service.delete_run(run_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Test run not found")

    return {"message": "Test run deleted"}
