"""Automation worker — consumes events, matches rules, executes actions."""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from app.database import async_session_maker
from app.models.db_models import AutomationRun, generate_uuid
from app.repositories.automation_repo import (
    AutomationRuleRepository,
    AutomationRunRepository,
)
from app.repositories.task_repo import TaskRepository
from app.services.automation_service import (
    AutomationExecutor,
    build_context,
    match_rules,
)
from app.services.redis_client import get_redis
from app.services.redis_streams import ack, consume, create_group

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STREAM = "el:events"
CONSUMER_GROUP = "automations"
CONSUMER_NAME = f"auto-{uuid.uuid4().hex[:8]}"
POLL_INTERVAL = 30


async def handle_event(event: dict[str, Any]) -> None:
    """Process a single event: match rules and execute actions."""
    event_type = event.get("type", "")
    project_id = event.get("project_id", "")
    payload = json.loads(event.get("payload", "{}"))

    if not project_id or event_type != "task.status_changed":
        return

    async with async_session_maker() as db:
        rule_repo = AutomationRuleRepository(db)
        task_repo = TaskRepository(db)
        executor = AutomationExecutor(db)

        rules = await rule_repo.get_active_rules(project_id, event_type)
        parsed_event = {"type": event_type, "payload": payload}
        matched = match_rules(parsed_event, rules)

        if not matched:
            return

        task_id = payload.get("id")
        task = await task_repo.get_by_id_full(task_id) if task_id else None

        for rule in matched:
            run = AutomationRun(
                id=generate_uuid(),
                rule_id=rule.id,
                task_id=task_id,
                status="pending",
                trigger_event=event_type,
                trigger_payload=payload,
                actions_log=[],
            )
            db.add(run)
            await db.flush()

            context = build_context(task, payload) if task else {}
            actions = rule.actions or []
            actions_log = []

            for action in actions:
                try:
                    result = await executor.execute_action(action, task, context)
                except Exception as e:
                    result = {"status": "error", "error": str(e)}

                actions_log.append({
                    "type": action.get("type"),
                    "status": result.get("status", "error"),
                    "result": result.get("result"),
                    "error": result.get("error"),
                    "executed_at": datetime.utcnow().isoformat(),
                })

                if result.get("status") == "error":
                    run.status = "failed"
                    run.error = result.get("error", "Action failed")
                    run.actions_log = actions_log
                    run.finished_at = datetime.utcnow()
                    break

                if result.get("async"):
                    # Pipeline action — save state for polling
                    run.status = "running"
                    run.gitlab_pipeline_id = result.get("pipeline_id")
                    run.gitlab_connection_id = result.get("connection_id")
                    run.gitlab_project_path = str(result.get("gitlab_project_id", ""))
                    run.actions_log = actions_log

                    # Save remaining actions + sub-actions as pending
                    pending = action.get("params", {})
                    run.pending_actions = {
                        "on_success": pending.get("on_success", []),
                        "on_failure": pending.get("on_failure", []),
                    }
                    break
            else:
                # All actions completed successfully
                run.status = "completed"
                run.actions_log = actions_log
                run.finished_at = datetime.utcnow()

            await db.commit()
            logger.info(
                f"Rule '{rule.name}' → {run.status} "
                f"(task={task_id}, run={run.id[:8]})"
            )


async def event_loop() -> None:
    """Consume events from Redis stream."""
    logger.info(f"Event loop started ({CONSUMER_NAME})")
    while True:
        try:
            messages = await consume(STREAM, CONSUMER_GROUP, CONSUMER_NAME, count=5)
            for msg in messages:
                try:
                    await handle_event(msg.data)
                except Exception as e:
                    logger.error(f"Event error {msg.id}: {e}")
                await ack(STREAM, CONSUMER_GROUP, msg.id)
        except Exception as e:
            logger.error(f"Event loop error: {e}")
            await asyncio.sleep(2)


async def pipeline_poll_loop() -> None:
    """Poll running pipelines and resolve pending actions."""
    logger.info("Pipeline poll loop started")
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            async with async_session_maker() as db:
                run_repo = AutomationRunRepository(db)
                executor = AutomationExecutor(db)
                runs = await run_repo.get_running_pipelines()

                for run in runs:
                    try:
                        timed_out = await executor.check_timeout(run)
                        if not timed_out:
                            await executor.resolve_pipeline(run)
                        await db.commit()
                    except Exception as e:
                        logger.error(f"Pipeline poll error run={run.id[:8]}: {e}")
                        await db.rollback()
        except Exception as e:
            logger.error(f"Poll loop error: {e}")


async def main() -> None:
    """Worker entrypoint."""
    logger.info("Automation worker starting")
    await get_redis()
    await create_group(STREAM, CONSUMER_GROUP)
    logger.info(f"Listening on {STREAM} (group={CONSUMER_GROUP})")

    await asyncio.gather(
        event_loop(),
        pipeline_poll_loop(),
    )


if __name__ == "__main__":
    asyncio.run(main())
