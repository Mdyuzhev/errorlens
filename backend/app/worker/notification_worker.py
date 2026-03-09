"""Notification worker — consumes domain events and creates notifications."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.db_models import Notification, ProjectMember, TestCase, TestPlanRun
from app.services.redis_client import get_redis
from app.services.redis_streams import ack, consume, create_group

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STREAM = "el:events"
CONSUMER_GROUP = "notifications"
CONSUMER_NAME = f"notif-{uuid.uuid4().hex[:8]}"


async def notify_user(
    db: AsyncSession,
    user_id: str,
    event_id: str,
    event_type: str,
    title: str,
    body: str | None,
    entity_type: str | None,
    entity_id: str | None,
) -> None:
    """Insert notification idempotently (ON CONFLICT DO NOTHING)."""
    stmt = pg_insert(Notification).values(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event_id=event_id,
        type=event_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    ).on_conflict_do_nothing(constraint="uq_notification_user_event")
    await db.execute(stmt)


async def get_project_admins(db: AsyncSession, project_id: str) -> list[str]:
    """Get user_ids of admin/owner members of a project."""
    result = await db.execute(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.role.in_(["admin", "owner"]),
        )
    )
    return [r[0] for r in result.all()]


async def handle_event(db: AsyncSession, event: dict[str, Any]) -> None:
    """Dispatch event to appropriate notification handler."""
    event_id = event.get("event_id", "")
    event_type = event.get("type", "")
    payload = json.loads(event.get("payload", "{}"))
    project_id = event.get("project_id", "")

    if event_type == "task.assigned":
        new_assignee = payload.get("new_assignee_id")
        if new_assignee:
            await notify_user(
                db, new_assignee, event_id, event_type,
                f"Задача назначена: {payload.get('title', '')}",
                None, "task", payload.get("id"),
            )

    elif event_type == "task.status_changed":
        assignee = payload.get("assignee_id")
        if assignee:
            new_status = payload.get("new_status", "")
            await notify_user(
                db, assignee, event_id, event_type,
                f"Задача {payload.get('title', '')}: {new_status}",
                None, "task", payload.get("id"),
            )

    elif event_type == "testcase.status_changed":
        tc_id = payload.get("id")
        if tc_id:
            result = await db.execute(
                select(TestCase.created_by).where(TestCase.id == tc_id)
            )
            created_by = result.scalar_one_or_none()
            if created_by:
                await notify_user(
                    db, created_by, event_id, event_type,
                    f"Тест-кейс {payload.get('title', '')}: {payload.get('new_status', '')}",
                    None, "testcase", tc_id,
                )

    elif event_type == "testplan_run.completed":
        run_id = payload.get("run_id")
        if run_id:
            result = await db.execute(
                select(TestPlanRun.started_by).where(TestPlanRun.id == run_id)
            )
            started_by = result.scalar_one_or_none()
            if started_by:
                await notify_user(
                    db, started_by, event_id, event_type,
                    f"Прогон завершён: {payload.get('plan_name', '')}",
                    f"Passed: {payload.get('passed', 0)}, Failed: {payload.get('failed', 0)}",
                    "testplan_run", run_id,
                )

            # Notify admins if there are failures
            failed = payload.get("failed", 0)
            if failed > 0 and project_id:
                admins = await get_project_admins(db, project_id)
                for admin_id in admins:
                    if admin_id != started_by:
                        await notify_user(
                            db, admin_id, event_id, event_type,
                            f"Прогон с ошибками: {payload.get('plan_name', '')}",
                            f"Failed: {failed}",
                            "testplan_run", run_id,
                        )

    elif event_type == "session.analyzed":
        severity = payload.get("severity", "")
        if severity == "critical" and project_id:
            admins = await get_project_admins(db, project_id)
            for admin_id in admins:
                await notify_user(
                    db, admin_id, event_id, event_type,
                    f"Критическая сессия: {payload.get('summary', '')[:100]}",
                    None, "session", payload.get("session_id"),
                )

    await db.commit()


async def main() -> None:
    """Worker main loop."""
    logger.info(f"Notification worker starting: {CONSUMER_NAME}")

    await get_redis()
    await create_group(STREAM, CONSUMER_GROUP)

    logger.info(f"Listening on stream {STREAM}")

    while True:
        try:
            messages = await consume(STREAM, CONSUMER_GROUP, CONSUMER_NAME, count=5)
            if not messages:
                continue

            async with async_session_maker() as db:
                for msg in messages:
                    try:
                        await handle_event(db, msg.data)
                    except Exception as e:
                        logger.error(f"Error handling event {msg.id}: {e}")
                    await ack(STREAM, CONSUMER_GROUP, msg.id)

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
