"""Session management API endpoints."""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyzer import analyze_errors
from app.database import get_db
from app.models.db_models import AnalysisResult, Session, SessionData
from app.models_pydantic import AnalyzeRequest, ConsoleLogEntry, JSException, NetworkError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# === Pydantic schemas for API ===

class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    url: str
    user_agent: str
    recording_duration_ms: int = 0
    record_mode: str = "errors"
    console_logs: list[dict] = Field(default_factory=list)
    network_errors: list[dict] = Field(default_factory=list)
    js_exceptions: list[dict] = Field(default_factory=list)
    recorded_requests: list[dict] = Field(default_factory=list)
    screenshot: Optional[str] = None


class SessionResponse(BaseModel):
    """Session response."""
    id: str
    url: str
    user_agent: str
    created_at: str
    recording_duration_ms: int
    record_mode: str
    has_analysis: bool
    events_count: int


class SessionDetailResponse(BaseModel):
    """Detailed session response with data and analysis."""
    id: str
    url: str
    user_agent: str
    created_at: str
    recording_duration_ms: int
    record_mode: str
    console_logs: list[dict]
    network_errors: list[dict]
    js_exceptions: list[dict]
    recorded_requests: list[dict]
    screenshot: Optional[str]
    analysis: Optional[dict]


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""
    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class SessionCreateResponse(BaseModel):
    """Response after creating session."""
    session_id: str
    analysis: Optional[dict] = None


# === API Endpoints ===

@router.post("", response_model=SessionCreateResponse)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> SessionCreateResponse:
    """
    Create a new session and trigger AI analysis.

    Saves session data and runs analysis, returning session_id and results.
    """
    session_id = str(uuid4())

    # Create session
    session = Session(
        id=session_id,
        url=request.url,
        user_agent=request.user_agent,
        recording_duration_ms=request.recording_duration_ms,
        record_mode=request.record_mode,
    )
    db.add(session)

    # Create session data
    session_data = SessionData(
        session_id=session_id,
        console_logs=request.console_logs,
        network_errors=request.network_errors,
        js_exceptions=request.js_exceptions,
        recorded_requests=request.recorded_requests,
        screenshot=request.screenshot,
    )
    db.add(session_data)

    # Run analysis if there's data to analyze
    analysis_dict = None
    total_events = len(request.console_logs) + len(request.js_exceptions) + len(request.network_errors)

    if total_events > 0:
        try:
            # Convert to AnalyzeRequest format
            analyze_request = AnalyzeRequest(
                url=request.url,
                user_agent=request.user_agent,
                recording_duration_ms=request.recording_duration_ms,
                console_logs=[ConsoleLogEntry(**log) for log in request.console_logs],
                js_exceptions=[JSException(**exc) for exc in request.js_exceptions],
                network_errors=[NetworkError(**err) for err in request.network_errors],
                screenshot=request.screenshot,
            )

            result = await analyze_errors(analyze_request)

            # Save analysis result
            analysis = AnalysisResult(
                session_id=session_id,
                summary=result.summary,
                probable_cause=result.probable_cause,
                suggested_fix=result.suggested_fix,
                severity=result.severity,
                details=result.details,
                raw_events_count=result.raw_events_count,
            )
            db.add(analysis)

            analysis_dict = {
                "summary": result.summary,
                "probable_cause": result.probable_cause,
                "suggested_fix": result.suggested_fix,
                "severity": result.severity,
                "details": result.details,
                "raw_events_count": result.raw_events_count,
            }

        except Exception as e:
            logger.error(f"Analysis failed for session {session_id}: {e}")
            # Session is still saved, just without analysis

    await db.commit()
    logger.info(f"Created session {session_id}")

    return SessionCreateResponse(
        session_id=session_id,
        analysis=analysis_dict,
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """
    List all sessions with pagination.

    Returns sessions sorted by creation date (newest first).
    """
    # Get total count
    count_query = select(func.count(Session.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get sessions with analysis info
    query = (
        select(Session)
        .options(selectinload(Session.data), selectinload(Session.analysis))
        .order_by(desc(Session.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        events_count = 0
        if s.data:
            events_count = (
                len(s.data.console_logs or []) +
                len(s.data.network_errors or []) +
                len(s.data.js_exceptions or [])
            )

        items.append(SessionResponse(
            id=s.id,
            url=s.url,
            user_agent=s.user_agent,
            created_at=s.created_at.isoformat(),
            recording_duration_ms=s.recording_duration_ms,
            record_mode=s.record_mode,
            has_analysis=s.analysis is not None,
            events_count=events_count,
        ))

    return SessionListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    """
    Get detailed session information including data and analysis.
    """
    query = (
        select(Session)
        .options(selectinload(Session.data), selectinload(Session.analysis))
        .where(Session.id == session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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

    return SessionDetailResponse(
        id=session.id,
        url=session.url,
        user_agent=session.user_agent,
        created_at=session.created_at.isoformat(),
        recording_duration_ms=session.recording_duration_ms,
        record_mode=session.record_mode,
        console_logs=session.data.console_logs if session.data else [],
        network_errors=session.data.network_errors if session.data else [],
        js_exceptions=session.data.js_exceptions if session.data else [],
        recorded_requests=session.data.recorded_requests if session.data else [],
        screenshot=session.data.screenshot if session.data else None,
        analysis=analysis_dict,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a session and all related data.
    """
    query = select(Session).where(Session.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()

    logger.info(f"Deleted session {session_id}")
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/export/{format}")
async def export_session(
    session_id: str,
    format: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export session in specified format.

    Supported formats: markdown, postman, pytest
    """
    query = (
        select(Session)
        .options(selectinload(Session.data), selectinload(Session.analysis))
        .where(Session.id == session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if format == "markdown":
        content = _export_markdown(session)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=errorlens-{session_id[:8]}.md"}
        )
    elif format == "postman":
        from app.generators import generate_postman_collection
        from app.models_pydantic import ExportPostmanRequest, RecordedRequest

        if not session.data or not session.data.recorded_requests:
            raise HTTPException(status_code=400, detail="No recorded requests to export")

        request = ExportPostmanRequest(
            recorded_requests=[
                RecordedRequest(**req) for req in session.data.recorded_requests
            ],
            collection_name=f"ErrorLens - {session.url[:50]}",
            base_url_variable=True,
            generate_tests=True,
        )
        result = generate_postman_collection(request)

        import json
        return Response(
            content=json.dumps(result.collection, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=errorlens-{session_id[:8]}.postman_collection.json"}
        )
    elif format == "pytest":
        from app.generators import generate_pytest_file
        from app.models_pydantic import RecordedHttpExchange

        if not session.data or not session.data.recorded_requests:
            raise HTTPException(status_code=400, detail="No recorded requests to export")

        # Convert dicts to RecordedHttpExchange objects
        exchanges = [
            RecordedHttpExchange(**req) for req in session.data.recorded_requests
        ]

        content = generate_pytest_file(
            recorded_requests=exchanges,
            test_name=f"test_session_{session_id[:8]}",
        )

        return Response(
            content=content,
            media_type="text/x-python",
            headers={"Content-Disposition": f"attachment; filename=test_session_{session_id[:8]}.py"}
        )
    elif format == "restassured":
        from app.generators import generate_restassured_file, generate_pom_xml
        from app.models_pydantic import RecordedHttpExchange
        import zipfile
        import io

        if not session.data or not session.data.recorded_requests:
            raise HTTPException(status_code=400, detail="No recorded requests to export")

        # Convert dicts to RecordedHttpExchange objects
        exchanges = [
            RecordedHttpExchange(**req) for req in session.data.recorded_requests
        ]

        class_name = f"Session{session_id[:8].replace('-', '').upper()}Test"
        java_code = generate_restassured_file(exchanges, class_name=class_name)

        # Return ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            package_path = "com/errorlens/tests"
            zf.writestr(f"src/test/java/{package_path}/{class_name}.java", java_code)
            zf.writestr("pom.xml", generate_pom_xml())
            zf.writestr("README.md", "# Run: mvn test")

        zip_buffer.seek(0)
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{class_name}.zip"'
            }
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


def _export_markdown(session: Session) -> str:
    """Generate markdown export for session."""
    lines = [
        f"# ErrorLens Report",
        f"",
        f"**URL:** {session.url}",
        f"**Date:** {session.created_at.isoformat()}",
        f"**Duration:** {session.recording_duration_ms}ms",
        f"",
    ]

    if session.analysis:
        lines.extend([
            f"## Analysis",
            f"",
            f"**Severity:** {session.analysis.severity.upper()}",
            f"",
            f"### Summary",
            f"{session.analysis.summary}",
            f"",
            f"### Probable Cause",
            f"{session.analysis.probable_cause}",
            f"",
            f"### Suggested Fix",
            f"{session.analysis.suggested_fix}",
            f"",
        ])
        if session.analysis.details:
            lines.extend([
                f"### Details",
                f"```",
                f"{session.analysis.details}",
                f"```",
                f"",
            ])

    if session.data:
        if session.data.console_logs:
            lines.extend([
                f"## Console Logs ({len(session.data.console_logs)})",
                f"",
            ])
            for log in session.data.console_logs[:10]:
                lines.append(f"- [{log.get('level', 'log')}] {log.get('message', '')[:100]}")
            if len(session.data.console_logs) > 10:
                lines.append(f"- ... and {len(session.data.console_logs) - 10} more")
            lines.append("")

        if session.data.network_errors:
            lines.extend([
                f"## Network Errors ({len(session.data.network_errors)})",
                f"",
            ])
            for err in session.data.network_errors[:5]:
                lines.append(f"- {err.get('method', 'GET')} {err.get('url', '')[:80]} → {err.get('status', '?')}")
            lines.append("")

    lines.extend([
        f"---",
        f"*Generated by ErrorLens*",
    ])

    return "\n".join(lines)
