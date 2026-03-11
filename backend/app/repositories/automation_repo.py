"""Repository for automation rules and runs."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.db_models import AutomationRule, AutomationRun
from app.repositories.base import BaseRepository


class AutomationRuleRepository(BaseRepository[AutomationRule]):
    """Data access for automation rules."""

    def __init__(self, db: AsyncSession):
        super().__init__(AutomationRule, db)

    async def get_active_rules(
        self, project_id: str, event_type: str
    ) -> list[AutomationRule]:
        """Get active rules for project matching event type."""
        stmt = (
            select(AutomationRule)
            .where(
                AutomationRule.project_id == project_id,
                AutomationRule.is_active.is_(True),
                AutomationRule.trigger_event == event_type,
            )
            .options(joinedload(AutomationRule.task_type))
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_rules_for_project(
        self, project_id: str
    ) -> list[AutomationRule]:
        """Get all rules for project (including inactive)."""
        stmt = (
            select(AutomationRule)
            .where(AutomationRule.project_id == project_id)
            .options(joinedload(AutomationRule.task_type))
            .order_by(AutomationRule.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())


class AutomationRunRepository(BaseRepository[AutomationRun]):
    """Data access for automation runs."""

    def __init__(self, db: AsyncSession):
        super().__init__(AutomationRun, db)

    async def get_running_pipelines(self) -> list[AutomationRun]:
        """Get runs with status=running and pipeline_id set (for polling)."""
        stmt = (
            select(AutomationRun)
            .where(
                AutomationRun.status == "running",
                AutomationRun.gitlab_pipeline_id.is_not(None),
            )
            .options(joinedload(AutomationRun.rule))
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_runs_for_rule(
        self, rule_id: str, limit: int = 20
    ) -> list[AutomationRun]:
        """Get recent runs for a specific rule."""
        stmt = (
            select(AutomationRun)
            .where(AutomationRun.rule_id == rule_id)
            .order_by(AutomationRun.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_runs_for_task(
        self, task_id: str, limit: int = 5
    ) -> list[AutomationRun]:
        """Get recent runs for a specific task."""
        stmt = (
            select(AutomationRun)
            .where(AutomationRun.task_id == task_id)
            .options(joinedload(AutomationRun.rule))
            .order_by(AutomationRun.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def count_recent_runs(
        self, rule_id: str, days: int = 7
    ) -> int:
        """Count runs for a rule in the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(func.count())
            .select_from(AutomationRun)
            .where(
                AutomationRun.rule_id == rule_id,
                AutomationRun.started_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
