"""Automations API router — CRUD for rules and run history."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.repositories.automation_repo import (
    AutomationRuleRepository,
    AutomationRunRepository,
)

router = APIRouter(prefix="/api/v1/automations", tags=["automations"])


# ── Schemas ──────────────────────────────────────────────


class CreateRuleRequest(BaseModel):
    project_id: str
    task_type_id: str | None = None
    name: str
    trigger_event: str
    trigger_conditions: dict = {}
    actions: list[dict] = []
    is_active: bool = True


class UpdateRuleRequest(BaseModel):
    task_type_id: str | None = None
    name: str | None = None
    trigger_event: str | None = None
    trigger_conditions: dict | None = None
    actions: list[dict] | None = None
    is_active: bool | None = None


# ── Helpers ──────────────────────────────────────────────


def _rule_to_dict(rule, runs_count: int = 0) -> dict:
    return {
        "id": rule.id,
        "project_id": rule.project_id,
        "task_type_id": rule.task_type_id,
        "task_type_name": rule.task_type.name if rule.task_type else None,
        "name": rule.name,
        "is_active": rule.is_active,
        "trigger_event": rule.trigger_event,
        "trigger_conditions": rule.trigger_conditions,
        "actions": rule.actions,
        "runs_count": runs_count,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def _run_to_dict(run) -> dict:
    return {
        "id": run.id,
        "rule_id": run.rule_id,
        "rule_name": run.rule.name if run.rule else None,
        "task_id": run.task_id,
        "status": run.status,
        "trigger_event": run.trigger_event,
        "trigger_payload": run.trigger_payload,
        "actions_log": run.actions_log,
        "gitlab_pipeline_id": run.gitlab_pipeline_id,
        "pending_actions": run.pending_actions,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error": run.error,
    }


# ── Rules CRUD ───────────────────────────────────────────


@router.get("/rules")
async def list_rules(
    project_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all automation rules for a project."""
    rule_repo = AutomationRuleRepository(db)
    run_repo = AutomationRunRepository(db)
    rules = await rule_repo.get_rules_for_project(project_id)

    result = []
    for rule in rules:
        count = await run_repo.count_recent_runs(rule.id)
        result.append(_rule_to_dict(rule, count))
    return result


@router.post("/rules", status_code=201)
async def create_rule(
    body: CreateRuleRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new automation rule."""
    rule_repo = AutomationRuleRepository(db)
    rule = await rule_repo.create(body.model_dump())
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    body: UpdateRuleRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update an automation rule."""
    rule_repo = AutomationRuleRepository(db)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    data["updated_at"] = datetime.utcnow()
    rule = await rule_repo.update(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.commit()
    return _rule_to_dict(rule)


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an automation rule."""
    rule_repo = AutomationRuleRepository(db)
    deleted = await rule_repo.delete(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.commit()


# ── Runs ─────────────────────────────────────────────────


@router.get("/rules/{rule_id}/runs")
async def list_rule_runs(
    rule_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get recent runs for a rule."""
    run_repo = AutomationRunRepository(db)
    runs = await run_repo.get_runs_for_rule(rule_id)
    return [_run_to_dict(r) for r in runs]


@router.get("/runs")
async def list_runs(
    task_id: str | None = None,
    limit: int = 20,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get runs, optionally filtered by task_id."""
    run_repo = AutomationRunRepository(db)
    if task_id:
        runs = await run_repo.get_runs_for_task(task_id, limit=limit)
    else:
        runs = await run_repo.get_all(limit=limit, order_by=None)
    return [_run_to_dict(r) for r in runs]


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get details of a single run."""
    run_repo = AutomationRunRepository(db)
    run = await run_repo.get_by_id(run_id, load_relations=["rule"])
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_dict(run)
