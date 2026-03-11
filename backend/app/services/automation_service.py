"""Automation service — rule matching, action execution, pipeline resolution."""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import (
    AutomationRule,
    AutomationRun,
    TaskComment,
    generate_uuid,
)
from app.repositories.gitlab_connection_repo import GitLabConnectionRepository
from app.repositories.task_repo import TaskRepository
from app.repositories.task_type_repo import TaskTypeRepository
from app.services.gitlab_service import GitLabService

logger = logging.getLogger(__name__)


def match_rules(event: dict, rules: list[AutomationRule]) -> list[AutomationRule]:
    """Filter rules that match the event conditions."""
    matched = []
    for rule in rules:
        if rule.trigger_event != event.get("type", ""):
            continue
        cond = rule.trigger_conditions or {}
        payload = event.get("payload", {})
        if "to_status_id" in cond and cond["to_status_id"] != payload.get("to_status_id"):
            continue
        if "from_status_id" in cond and cond["from_status_id"] != payload.get("from_status_id"):
            continue
        if rule.task_type_id and rule.task_type_id != payload.get("type_id"):
            continue
        matched.append(rule)
    return matched


def build_context(
    task: Any, event_payload: dict, pipeline: dict | None = None
) -> dict[str, str]:
    """Build template variable context."""
    ctx = {
        "task.human_id": getattr(task, "human_id", "") or "",
        "task.title": getattr(task, "title", ""),
        "task.id": str(getattr(task, "id", "")),
    }
    if pipeline:
        ctx["pipeline.url"] = pipeline.get("web_url", "")
        ctx["pipeline.status"] = pipeline.get("status", "")
        ctx["pipeline.id"] = str(pipeline.get("id", ""))
    return ctx


def render_template(text: str, context: dict[str, str]) -> str:
    """Replace {{key}} placeholders with context values."""
    for key, value in context.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


class AutomationExecutor:
    """Executes automation actions against database and external services."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = TaskRepository(db)
        self.gitlab_service = GitLabService()

    async def execute_action(
        self, action: dict, task: Any, context: dict[str, str]
    ) -> dict[str, Any]:
        """Dispatch and execute a single action."""
        action_type = action.get("type", "")
        params = action.get("params", {})

        if action_type == "change_task_status":
            return await self._change_status(task, params, context)
        elif action_type == "add_comment":
            return await self._add_comment(task, params, context)
        elif action_type == "run_gitlab_pipeline":
            return await self._run_pipeline(task, params, context)
        else:
            return {"status": "error", "error": f"Unknown action type: {action_type}"}

    async def _change_status(
        self, task: Any, params: dict, context: dict[str, str]
    ) -> dict[str, Any]:
        """Change task status bypassing workflow validation."""
        new_status_id = params.get("status_id")
        if not new_status_id:
            return {"status": "error", "error": "Missing status_id in params"}

        type_repo = TaskTypeRepository(self.db)
        new_status = await type_repo.get_status_by_id(new_status_id)
        if not new_status:
            return {"status": "error", "error": f"Status {new_status_id} not found"}

        task.status_id = new_status_id
        task.status = new_status.slug
        task.updated_at = datetime.utcnow()
        if new_status.slug == "done" and not task.completed_at:
            task.completed_at = datetime.utcnow()
        await self.db.flush()

        return {"status": "ok", "result": {"new_status": new_status.name}}

    async def _add_comment(
        self, task: Any, params: dict, context: dict[str, str]
    ) -> dict[str, Any]:
        """Add automation comment to task."""
        text = render_template(params.get("text", ""), context)
        comment = TaskComment(
            id=generate_uuid(),
            task_id=task.id,
            author_id=None,
            content=text,
        )
        self.db.add(comment)
        await self.db.flush()
        return {"status": "ok", "result": {"comment_id": comment.id}}

    async def _run_pipeline(
        self, task: Any, params: dict, context: dict[str, str]
    ) -> dict[str, Any]:
        """Trigger GitLab pipeline — returns async result."""
        connection_id = params.get("connection_id")
        project_id = params.get("gitlab_project_id")
        ref = render_template(params.get("ref", "main"), context)

        if not connection_id or not project_id:
            return {"status": "error", "error": "Missing connection_id or gitlab_project_id"}

        conn_repo = GitLabConnectionRepository(self.db)
        connection = await conn_repo.get_by_id(connection_id)
        if not connection:
            return {"status": "error", "error": f"GitLab connection {connection_id} not found"}

        variables = []
        for var in params.get("variables", []):
            variables.append({
                "key": var["key"],
                "value": render_template(var.get("value", ""), context),
            })

        pipeline = await self.gitlab_service.run_pipeline(
            connection, int(project_id), ref, variables or None
        )

        return {
            "status": "running",
            "async": True,
            "pipeline_id": pipeline["id"],
            "web_url": pipeline["web_url"],
            "connection_id": connection_id,
            "gitlab_project_id": project_id,
        }

    async def resolve_pipeline(
        self, run: AutomationRun
    ) -> None:
        """Check pipeline status and execute pending sub-actions."""
        if not run.gitlab_pipeline_id or not run.gitlab_connection_id:
            return

        conn_repo = GitLabConnectionRepository(self.db)
        connection = await conn_repo.get_by_id(run.gitlab_connection_id)
        if not connection:
            run.status = "failed"
            run.error = "GitLab connection not found"
            run.finished_at = datetime.utcnow()
            await self.db.flush()
            return

        # Determine project_id from run or connection
        gitlab_project_path = run.gitlab_project_path
        if not gitlab_project_path:
            run.status = "failed"
            run.error = "Missing gitlab_project_path"
            run.finished_at = datetime.utcnow()
            await self.db.flush()
            return

        pipeline = await self.gitlab_service.get_pipeline_status(
            connection, int(gitlab_project_path), run.gitlab_pipeline_id
        )

        status = pipeline.get("status", "")
        if status in ("pending", "running", "created"):
            return  # still running

        # Pipeline finished — execute sub-actions
        task = await self.task_repo.get_by_id_full(run.task_id) if run.task_id else None
        pipeline_context = build_context(task, {}, pipeline) if task else {}

        pending = run.pending_actions or {}
        actions_log = list(run.actions_log or [])

        if status == "success":
            sub_actions = pending.get("on_success", [])
        else:
            sub_actions = pending.get("on_failure", [])

        for action in sub_actions:
            result = await self.execute_action(action, task, pipeline_context)
            actions_log.append({
                "type": action.get("type"),
                "status": result.get("status", "error"),
                "result": result.get("result"),
                "error": result.get("error"),
                "executed_at": datetime.utcnow().isoformat(),
            })
            if result.get("status") == "error":
                run.status = "failed"
                run.error = result.get("error", "Sub-action failed")
                break
        else:
            run.status = "completed"

        run.actions_log = actions_log
        run.finished_at = datetime.utcnow()
        await self.db.flush()

    async def check_timeout(self, run: AutomationRun) -> bool:
        """Mark run as failed if stuck for >2 hours."""
        if run.started_at:
            elapsed = (datetime.utcnow() - run.started_at).total_seconds()
            if elapsed > 7200:
                run.status = "failed"
                run.error = "Pipeline poll timeout (>2h)"
                run.finished_at = datetime.utcnow()
                await self.db.flush()
                return True
        return False
