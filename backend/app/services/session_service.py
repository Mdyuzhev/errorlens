"""
Session Service - Business logic for session management.

Handles session creation, analysis, and export operations.
"""

import logging
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.analyzer import analyze_errors
from app.repositories.session_repo import SessionRepository
from app.models.db_models import Session
from app.models_pydantic import (
    AnalyzeRequest,
    ConsoleLogEntry,
    JSException,
    NetworkError,
    RecordedRequest,
    RecordedHttpExchange,
    ExportPostmanRequest,
)

logger = logging.getLogger(__name__)


class SessionService:
    """Service for session business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SessionRepository(db)

    async def create_session(
        self,
        url: str,
        user_agent: str,
        recording_duration_ms: int = 0,
        record_mode: str = "errors",
        console_logs: List[dict] = None,
        network_errors: List[dict] = None,
        js_exceptions: List[dict] = None,
        recorded_requests: List[dict] = None,
        screenshot: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new session with data and run AI analysis.

        Returns dict with session_id and analysis results.
        """
        console_logs = console_logs or []
        network_errors = network_errors or []
        js_exceptions = js_exceptions or []
        recorded_requests = recorded_requests or []

        session_id = str(uuid4())

        # Create session with data
        session = await self.repo.create_full_session(
            session_data={
                "id": session_id,
                "url": url,
                "user_agent": user_agent,
                "recording_duration_ms": recording_duration_ms,
                "record_mode": record_mode,
                "project_id": project_id,
            },
            captured_data={
                "console_logs": console_logs,
                "network_errors": network_errors,
                "js_exceptions": js_exceptions,
                "recorded_requests": recorded_requests,
                "screenshot": screenshot,
            },
        )

        # Run analysis if there's data
        analysis_dict = None
        total_events = len(console_logs) + len(js_exceptions) + len(network_errors)

        if total_events > 0:
            analysis_dict = await self._run_analysis(
                session_id=session_id,
                url=url,
                user_agent=user_agent,
                recording_duration_ms=recording_duration_ms,
                console_logs=console_logs,
                js_exceptions=js_exceptions,
                network_errors=network_errors,
                screenshot=screenshot,
            )

        await self.db.commit()
        logger.info(f"Created session {session_id}")

        return {
            "session_id": session_id,
            "analysis": analysis_dict,
        }

    async def _run_analysis(
        self,
        session_id: str,
        url: str,
        user_agent: str,
        recording_duration_ms: int,
        console_logs: List[dict],
        js_exceptions: List[dict],
        network_errors: List[dict],
        screenshot: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Run AI analysis on session data."""
        try:
            analyze_request = AnalyzeRequest(
                url=url,
                user_agent=user_agent,
                recording_duration_ms=recording_duration_ms,
                console_logs=[ConsoleLogEntry(**log) for log in console_logs],
                js_exceptions=[JSException(**exc) for exc in js_exceptions],
                network_errors=[NetworkError(**err) for err in network_errors],
                screenshot=screenshot,
            )

            result = await analyze_errors(analyze_request)

            # Save analysis to DB
            await self.repo.add_analysis(
                session_id=session_id,
                analysis_data={
                    "summary": result.summary,
                    "probable_cause": result.probable_cause,
                    "suggested_fix": result.suggested_fix,
                    "severity": result.severity,
                    "details": result.details,
                    "raw_events_count": result.raw_events_count,
                },
            )

            return {
                "summary": result.summary,
                "probable_cause": result.probable_cause,
                "suggested_fix": result.suggested_fix,
                "severity": result.severity,
                "details": result.details,
                "raw_events_count": result.raw_events_count,
            }

        except Exception as e:
            logger.error(f"Analysis failed for session {session_id}: {e}")
            return None

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session with all related data."""
        return await self.repo.get_with_data(session_id)

    async def list_sessions(
        self,
        limit: int = 20,
        offset: int = 0,
        mode: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get paginated list of sessions.

        Args:
            limit: Max number of sessions to return
            offset: Number of sessions to skip
            mode: Filter by record_mode ('errors' or 'all')
            project_id: Filter by project ID for multi-tenancy

        Returns:
            Dict with items, total, limit, offset
        """
        # Get total count (filtered by project_id)
        total = await self.repo.count(project_id=project_id)

        # Get sessions with data (filtered by project_id)
        sessions = await self.repo.get_recent(
            limit=limit, skip=offset, mode=mode, project_id=project_id
        )

        items = []
        for s in sessions:
            events_count = self._count_events(s)
            items.append(self._session_to_response(s, events_count))

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def delete_session(self, session_id: str) -> bool:
        """Delete session and all related data."""
        session = await self.repo.get_by_id(session_id)
        if not session:
            return False

        await self.repo.delete(session_id)
        await self.db.commit()
        logger.info(f"Deleted session {session_id}")
        return True

    async def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get session statistics."""
        return await self.repo.get_stats(days=days)

    def _count_events(self, session: Session) -> int:
        """Count total events in session."""
        if not session.data:
            return 0
        return (
            len(session.data.console_logs or [])
            + len(session.data.network_errors or [])
            + len(session.data.js_exceptions or [])
        )

    def _session_to_response(self, session: Session, events_count: int) -> Dict[str, Any]:
        """Convert Session model to response dict."""
        return {
            "id": session.id,
            "url": session.url,
            "user_agent": session.user_agent,
            "created_at": session.created_at.isoformat(),
            "recording_duration_ms": session.recording_duration_ms,
            "record_mode": session.record_mode,
            "has_analysis": session.analysis is not None,
            "has_errors": session.record_mode == "errors",
            "has_requests": session.record_mode == "all",
            "events_count": events_count,
            "testit_url": session.testit_url,
            "testit_id": session.testit_id,
        }

    def session_to_detail(self, session: Session) -> Dict[str, Any]:
        """Convert Session model to detailed response dict."""
        analysis_dict = None
        if session.analysis:
            analysis_dict = {
                "summary": session.analysis.summary,
                "probable_cause": session.analysis.probable_cause,
                "suggested_fix": session.analysis.suggested_fix,
                "severity": session.analysis.severity,
                "details": session.analysis.details,
                "raw_events_count": session.analysis.raw_events_count,
                "analyzed_at": session.analysis.analyzed_at.isoformat(),
            }

        return {
            "id": session.id,
            "url": session.url,
            "user_agent": session.user_agent,
            "created_at": session.created_at.isoformat(),
            "recording_duration_ms": session.recording_duration_ms,
            "record_mode": session.record_mode,
            "console_logs": session.data.console_logs if session.data else [],
            "network_errors": session.data.network_errors if session.data else [],
            "js_exceptions": session.data.js_exceptions if session.data else [],
            "recorded_requests": session.data.recorded_requests if session.data else [],
            "screenshot": session.data.screenshot if session.data else None,
            "analysis": analysis_dict,
            "testit_url": session.testit_url,
            "testit_id": session.testit_id,
        }
