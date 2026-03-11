"""Test Plans API router - thin controller."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import check_project_access, get_default_project, require_auth
from app.models.user import User
from app.services.test_plan_service import TestPlanService

router = APIRouter(prefix="/v1/test-plans", tags=["test-plans"])


# --- Schemas ---

class CreatePlanRequest(BaseModel):
    name: str
    description: str | None = None
    status: str = "draft"
    project_id: str | None = None


class UpdatePlanRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class AddCasesRequest(BaseModel):
    testcase_ids: list[str]


class ReorderRequest(BaseModel):
    ordered_ids: list[str]


class CreateRunRequest(BaseModel):
    name: str


class RecordResultRequest(BaseModel):
    status: str
    comment: str | None = None
    error_details: str | None = None


# --- Run endpoints (must be BEFORE /{plan_id} to avoid route conflict) ---

@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get run detail with results."""
    service = TestPlanService(db)
    detail = await service.get_run_detail(run_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail


@router.put("/runs/{run_id}/results/{testcase_id}")
async def record_result(
    run_id: str,
    testcase_id: str,
    data: RecordResultRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Record or update result for a testcase in a run."""
    service = TestPlanService(db)
    return await service.record_result(
        run_id=run_id,
        testcase_id=testcase_id,
        status=data.status,
        comment=data.comment,
        error_details=data.error_details,
        executed_by=user.id,
    )


@router.post("/runs/{run_id}/finish")
async def finish_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Finish a run."""
    service = TestPlanService(db)
    run = await service.finish_run(run_id)
    return service.run_to_summary(run)


# --- Plan endpoints ---

@router.get("")
async def list_plans(
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List test plans for a project."""
    if not project_id:
        project = await get_default_project(user, db)
        if not project:
            return []
        project_id = project.id

    await check_project_access(project_id, user, db)
    service = TestPlanService(db)
    return await service.list_plans(project_id)


@router.post("")
async def create_plan(
    data: CreatePlanRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create a new test plan."""
    project_id = data.project_id
    if not project_id:
        project = await get_default_project(user, db)
        if not project:
            raise HTTPException(status_code=400, detail="No project found")
        project_id = project.id

    await check_project_access(project_id, user, db)
    service = TestPlanService(db)
    plan = await service.create_plan(
        name=data.name,
        project_id=project_id,
        description=data.description,
        status=data.status,
        created_by=user.id,
    )
    return {
        "id": plan.id,
        "human_id": plan.human_id,
        "name": plan.name,
        "status": plan.status,
    }


@router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Get plan detail with cases."""
    service = TestPlanService(db)
    detail = await service.get_plan_detail(plan_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(detail["project_id"], user, db)
    return detail


@router.put("/{plan_id}")
async def update_plan(
    plan_id: str,
    data: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update test plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)

    updated = await service.update_plan(plan_id, **data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan updated"}


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete test plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)
    await service.delete_plan(plan_id)


# --- Cases endpoints ---

@router.post("/{plan_id}/cases", status_code=204)
async def add_cases(
    plan_id: str,
    data: AddCasesRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Add test cases to plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)
    await service.add_cases_to_plan(plan_id, data.testcase_ids)


@router.delete("/{plan_id}/cases/{testcase_id}", status_code=204)
async def remove_case(
    plan_id: str,
    testcase_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Remove a test case from plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)
    removed = await service.remove_case(plan_id, testcase_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Case not in plan")


@router.put("/{plan_id}/cases/reorder", status_code=204)
async def reorder_cases(
    plan_id: str,
    data: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Reorder test cases in plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)
    await service.reorder_cases(plan_id, data.ordered_ids)


# --- Plan run endpoints (nested under plan) ---

@router.post("/{plan_id}/runs")
async def start_run(
    plan_id: str,
    data: CreateRunRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Start a new run for a plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)

    run = await service.start_run(plan_id, data.name, started_by=user.id)
    return service.run_to_summary(run)


@router.get("/{plan_id}/runs")
async def list_runs(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List all runs for a plan."""
    service = TestPlanService(db)
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await check_project_access(plan.project_id, user, db)

    runs = await service.repo.list_runs(plan_id)
    return [service.run_to_summary(r) for r in runs]
