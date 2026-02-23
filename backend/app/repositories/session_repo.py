"""
Session Repository for browser session data access.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import AnalysisResult, Session, SessionData
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for Session model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_with_data(self, session_id: str) -> Session | None:
        """Get session with related SessionData and AnalysisResult."""
        query = (
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.data),
                selectinload(Session.analysis),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_recent(
        self,
        limit: int = 50,
        skip: int = 0,
        mode: str | None = None,
        project_id: str | None = None,
        include_unassigned: bool = True,
    ) -> list[Session]:
        """
        Get recent sessions ordered by creation date.

        Args:
            limit: Max sessions to return
            skip: Number of sessions to skip
            mode: Filter by record_mode
            project_id: Filter by project_id for multi-tenancy
            include_unassigned: Also include sessions without project_id
        """
        from sqlalchemy import or_

        query = (
            select(Session)
            .options(
                selectinload(Session.data),
                selectinload(Session.analysis),
            )
            .order_by(desc(Session.created_at))
        )

        if mode:
            query = query.where(Session.record_mode == mode)

        if project_id:
            if include_unassigned:
                # Include both: sessions with this project_id OR sessions without project_id
                query = query.where(
                    or_(Session.project_id == project_id, Session.project_id.is_(None))
                )
            else:
                query = query.where(Session.project_id == project_id)
        elif not include_unassigned:
            # No project_id filter but exclude unassigned - return nothing
            query = query.where(Session.project_id.isnot(None))

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        project_id: str | None = None,
        include_unassigned: bool = True,
    ) -> int:
        """Count sessions with project filtering."""
        from sqlalchemy import or_

        query = select(func.count()).select_from(Session)

        if project_id:
            if include_unassigned:
                query = query.where(
                    or_(Session.project_id == project_id, Session.project_id.is_(None))
                )
            else:
                query = query.where(Session.project_id == project_id)
        elif not include_unassigned:
            query = query.where(Session.project_id.isnot(None))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_by_url_pattern(
        self,
        url_pattern: str,
        limit: int = 50,
    ) -> list[Session]:
        """Get sessions matching URL pattern."""
        query = (
            select(Session)
            .where(Session.url.contains(url_pattern))
            .order_by(desc(Session.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_full_session(
        self,
        session_data: dict[str, Any],
        captured_data: dict[str, Any],
    ) -> Session:
        """Create session with associated SessionData."""
        # Create session
        session_instance = Session(**session_data)
        self.session.add(session_instance)
        await self.session.flush()

        # Create session data
        data_instance = SessionData(
            session_id=session_instance.id,
            console_logs=captured_data.get("console_logs", []),
            network_errors=captured_data.get("network_errors", []),
            js_exceptions=captured_data.get("js_exceptions", []),
            recorded_requests=captured_data.get("recorded_requests", []),
            screenshot=captured_data.get("screenshot"),
        )
        self.session.add(data_instance)
        await self.session.flush()

        await self.session.refresh(session_instance)
        return session_instance

    async def add_analysis(
        self,
        session_id: str,
        analysis_data: dict[str, Any],
    ) -> AnalysisResult:
        """Add analysis result to session."""
        analysis = AnalysisResult(
            session_id=session_id,
            summary=analysis_data.get("summary", ""),
            probable_cause=analysis_data.get("probable_cause", ""),
            suggested_fix=analysis_data.get("suggested_fix", ""),
            severity=analysis_data.get("severity", "medium"),
            details=analysis_data.get("details"),
            raw_events_count=analysis_data.get("raw_events_count", 0),
        )
        self.session.add(analysis)
        await self.session.flush()
        await self.session.refresh(analysis)
        return analysis

    async def get_stats(self, days: int = 30) -> dict[str, Any]:
        """Get session statistics for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total count
        total_query = select(func.count()).select_from(Session)
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        # Recent count
        recent_query = select(func.count()).select_from(Session).where(Session.created_at >= cutoff)
        recent_result = await self.session.execute(recent_query)
        recent = recent_result.scalar() or 0

        # By mode
        mode_query = (
            select(Session.record_mode, func.count())
            .where(Session.created_at >= cutoff)
            .group_by(Session.record_mode)
        )
        mode_result = await self.session.execute(mode_query)
        by_mode = {row[0]: row[1] for row in mode_result.all()}

        return {
            "total": total,
            "recent": recent,
            "by_mode": by_mode,
            "period_days": days,
        }

    async def update_testit_link(
        self,
        session_id: str,
        testit_id: int,
        testit_url: str,
    ) -> Session | None:
        """Update Test IT integration fields."""
        return await self.update(session_id, {"testit_id": testit_id, "testit_url": testit_url})
