"""Session management API endpoints - Thin controller."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

logger = logging.getLogger(__name__)
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.session_service import SessionService
from app.services.export_service import ExportService


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
    project_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Session response."""
    id: str
    url: str
    user_agent: str
    created_at: str
    recording_duration_ms: int
    record_mode: str
    has_analysis: bool
    has_errors: bool
    has_requests: bool
    events_count: int
    testit_url: Optional[str] = None
    testit_id: Optional[int] = None


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
    testit_url: Optional[str] = None
    testit_id: Optional[int] = None


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
    """Create a new session and trigger AI analysis."""
    logger.info(f"[SESSIONS] POST /sessions received - URL: {request.url}")
    logger.info(f"[SESSIONS] Payload: console_logs={len(request.console_logs)}, "
                f"network_errors={len(request.network_errors)}, "
                f"js_exceptions={len(request.js_exceptions)}, "
                f"recorded_requests={len(request.recorded_requests)}")

    # Validate that session has at least one event
    has_events = (
        request.console_logs or
        request.network_errors or
        request.js_exceptions or
        request.recorded_requests
    )
    if not has_events:
        raise HTTPException(
            status_code=400,
            detail="Session must contain at least one event (console_logs, network_errors, js_exceptions, or recorded_requests)"
        )

    service = SessionService(db)
    result = await service.create_session(
        url=request.url,
        user_agent=request.user_agent,
        recording_duration_ms=request.recording_duration_ms,
        record_mode=request.record_mode,
        console_logs=request.console_logs,
        network_errors=request.network_errors,
        js_exceptions=request.js_exceptions,
        recorded_requests=request.recorded_requests,
        screenshot=request.screenshot,
        project_id=request.project_id,
    )
    return SessionCreateResponse(**result)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> SessionListResponse:
    """List all sessions with pagination."""
    service = SessionService(db)
    result = await service.list_sessions(limit=limit, offset=offset)
    return SessionListResponse(**result)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> SessionDetailResponse:
    """Get detailed session information."""
    service = SessionService(db)
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(**service.session_to_detail(session))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> dict:
    """Delete a session and all related data."""
    service = SessionService(db)
    deleted = await service.delete_session(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/export/{format}")
async def export_session(
    session_id: str,
    format: str,
    subformat: str = "json",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> Response:
    """
    Export session in specified format.

    Supported formats: markdown, postman, pytest, restassured, testit
    """
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    export_service = ExportService()

    try:
        if format == "markdown":
            content = export_service.export_markdown(session)
        elif format == "postman":
            import json
            content = json.dumps(export_service.export_postman(session), indent=2)
        elif format == "pytest":
            content = export_service.export_pytest(session)
        elif format == "restassured":
            content = export_service.export_restassured(session)
        elif format == "testit":
            content = export_service.export_testit(session, subformat)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(
        content=content,
        media_type=export_service.get_content_type(format, subformat),
        headers={
            "Content-Disposition": f'attachment; filename="{export_service.get_filename(session_id, format, subformat)}"'
        },
    )
