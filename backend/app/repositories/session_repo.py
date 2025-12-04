"""
Session Repository for browser session data access.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.db_models import Session, SessionData, AnalysisResult


class SessionRepository(BaseRepository[Session]):
    """Repository for Session model with specialized queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(Session, session)

    async def get_with_data(self, session_id: str) -> Optional[Session]:
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
        mode: Optional[str] = None,
    ) -> List[Session]:
        """Get recent sessions ordered by creation date."""
        query = select(Session).order_by(desc(Session.created_at))

        if mode:
            query = query.where(Session.record_mode == mode)

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_url_pattern(
        self,
        url_pattern: str,
        limit: int = 50,
    ) -> List[Session]:
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
        session_data: Dict[str, Any],
        captured_data: Dict[str, Any],
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
        analysis_data: Dict[str, Any],
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

    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get session statistics for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total count
        total_query = select(func.count()).select_from(Session)
        total_result = await self.session.execute(total_query)
        total = total_result.scalar() or 0

        # Recent count
        recent_query = (
            select(func.count())
            .select_from(Session)
            .where(Session.created_at >= cutoff)
        )
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
    ) -> Optional[Session]:
        """Update Test IT integration fields."""
        return await self.update(
            session_id,
            {"testit_id": testit_id, "testit_url": testit_url}
        )
