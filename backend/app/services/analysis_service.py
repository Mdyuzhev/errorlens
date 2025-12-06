"""Analysis service - business logic for error analysis and ticket generation."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyzer import analyze_errors
from app.config import settings
from app.models.db_models import AnalysisResult, Session
from app.models_pydantic import (
    AnalyzeRequest,
    ConsoleLogEntry,
    JSException,
    NetworkError,
    RecordedHttpExchange,
)
from app.session_analyzer import analyze_session
from app.ticket_generator import generate_smart_ticket

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for error analysis and ticket generation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_errors(
        self,
        url: str,
        user_agent: str,
        console_logs: list[dict],
        js_exceptions: list[dict],
        network_errors: list[dict],
        screenshot: str | None = None,
        recording_duration_ms: int = 0,
    ) -> dict[str, Any]:
        """Analyze captured browser errors using AI."""
        # Validate limits
        if len(console_logs) > settings.max_console_logs:
            raise ValueError(f"Exceeded console_logs limit: max {settings.max_console_logs}")
        if len(network_errors) > settings.max_network_errors:
            raise ValueError(f"Exceeded network_errors limit: max {settings.max_network_errors}")

        total_events = len(console_logs) + len(js_exceptions) + len(network_errors)
        if total_events == 0:
            raise ValueError("No error data to analyze")

        logger.info(f"Analyzing {total_events} events from {url}")

        # Build request
        request = AnalyzeRequest(
            url=url,
            user_agent=user_agent,
            recording_duration_ms=recording_duration_ms,
            console_logs=[ConsoleLogEntry(**log) for log in console_logs],
            js_exceptions=[JSException(**exc) for exc in js_exceptions],
            network_errors=[NetworkError(**err) for err in network_errors],
            screenshot=screenshot,
        )

        result = await analyze_errors(request)
        logger.info(f"Analysis complete: severity={result.severity}")

        return {
            "summary": result.summary,
            "probable_cause": result.probable_cause,
            "suggested_fix": result.suggested_fix,
            "severity": result.severity,
            "details": result.details,
            "raw_events_count": result.raw_events_count,
        }

    def analyze_session_requests(
        self,
        recorded_requests: list[dict],
    ) -> dict[str, Any]:
        """Analyze recorded session for test generation."""
        if not recorded_requests:
            raise ValueError("No recorded requests to analyze")

        logger.info(f"Analyzing session with {len(recorded_requests)} requests")

        # Convert to pydantic models
        exchanges = [RecordedHttpExchange(**r) for r in recorded_requests]
        result = analyze_session(exchanges)

        # Transform variables
        variables = {
            name: {
                "name": name,
                "source_request_id": data["source_request_id"],
                "source_path": data["source_path"],
                "value": data["value"][:50] + "..." if len(data["value"]) > 50 else data["value"],
                "used_in": data["used_in"],
            }
            for name, data in result["variables"].items()
        }

        # Transform assertions
        assertions = {
            req_id: [
                {
                    "type": a["type"],
                    "path": a.get("path"),
                    "expected": str(a["expected"]),
                    "description": a["description"],
                }
                for a in assertion_list
            ]
            for req_id, assertion_list in result["assertions"].items()
        }

        logger.info(f"Analysis complete: {result['summary']}")

        return {
            "variables": variables,
            "groups": result["groups"],
            "assertions": assertions,
            "summary": result["summary"],
        }

    async def generate_ticket(
        self,
        session_id: str,
        format: str = "markdown",
        additional_info: str | None = None,
    ) -> dict[str, Any]:
        """Generate bug ticket from session analysis."""
        # Get session with analysis and data
        query = (
            select(Session)
            .options(selectinload(Session.analysis), selectinload(Session.data))
            .where(Session.id == session_id)
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            raise ValueError("Session not found")

        if not session.analysis:
            raise ValueError("Session has no analysis")

        analysis_dict = {
            "summary": session.analysis.summary,
            "probable_cause": session.analysis.probable_cause,
            "suggested_fix": session.analysis.suggested_fix,
            "severity": session.analysis.severity,
            "details": session.analysis.details,
        }

        session_data = session.data

        ticket = generate_smart_ticket(
            analysis=analysis_dict,
            url=session.url,
            user_agent=session.user_agent,
            recorded_requests=session_data.recorded_requests if session_data else [],
            console_logs=session_data.console_logs if session_data else [],
            js_exceptions=session_data.js_exceptions if session_data else [],
            additional_info=additional_info,
            format=format,
        )

        logger.info(f"Generated {format} ticket for session {session_id}")

        return ticket

    async def reanalyze_session(self, session_id: str) -> dict[str, Any] | None:
        """Re-run analysis on existing session."""
        query = select(Session).options(selectinload(Session.data)).where(Session.id == session_id)
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session or not session.data:
            return None

        data = session.data

        # Run analysis
        analysis_result = await self.analyze_errors(
            url=session.url,
            user_agent=session.user_agent,
            console_logs=data.console_logs or [],
            js_exceptions=data.js_exceptions or [],
            network_errors=data.network_errors or [],
            screenshot=data.screenshot,
            recording_duration_ms=session.recording_duration_ms or 0,
        )

        # Update or create analysis record
        if session.analysis:
            session.analysis.summary = analysis_result["summary"]
            session.analysis.probable_cause = analysis_result["probable_cause"]
            session.analysis.suggested_fix = analysis_result["suggested_fix"]
            session.analysis.severity = analysis_result["severity"]
            session.analysis.details = analysis_result["details"]
            session.analysis.raw_events_count = analysis_result["raw_events_count"]
        else:
            analysis = AnalysisResult(
                session_id=session_id,
                summary=analysis_result["summary"],
                probable_cause=analysis_result["probable_cause"],
                suggested_fix=analysis_result["suggested_fix"],
                severity=analysis_result["severity"],
                details=analysis_result["details"],
                raw_events_count=analysis_result["raw_events_count"],
            )
            self.db.add(analysis)

        await self.db.commit()
        logger.info(f"Re-analyzed session {session_id}")

        return analysis_result

    async def get_analysis_stats(self) -> dict[str, Any]:
        """Get analysis statistics."""
        # Count by severity
        query = select(Session).options(selectinload(Session.analysis))
        result = await self.db.execute(query)
        sessions = result.scalars().all()

        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        analyzed_count = 0

        for s in sessions:
            if s.analysis:
                analyzed_count += 1
                severity = s.analysis.severity or "medium"
                if severity in by_severity:
                    by_severity[severity] += 1

        return {
            "total_sessions": len(sessions),
            "analyzed": analyzed_count,
            "not_analyzed": len(sessions) - analyzed_count,
            "by_severity": by_severity,
        }
