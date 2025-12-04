"""Analysis and ticket generation endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analyzer import analyze_errors
from app.config import settings
from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.middleware.rate_limit import rate_limit_middleware
from app.models.db_models import Session
from app.models.user import User
from app.models_pydantic import (
    AnalyzeRequest,
    AnalyzeResponse,
    DetectedVariable,
    GenerateTicketRequest,
    GenerateTicketResponse,
    RequestAssertion,
    SessionAnalysisRequest,
    SessionAnalysisResponse,
)
from app.session_analyzer import analyze_session
from app.ticket_generator import generate_smart_ticket

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    http_request: Request,
    response: Response,
    remaining: int = Depends(rate_limit_middleware),
    _: User = Depends(require_auth),
) -> AnalyzeResponse:
    """Analyze captured browser errors using AI."""
    if remaining >= 0:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_day)

    if len(request.console_logs) > settings.max_console_logs:
        raise HTTPException(
            status_code=400,
            detail=f"Exceeded console_logs limit: max {settings.max_console_logs}",
        )
    if len(request.network_errors) > settings.max_network_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Exceeded network_errors limit: max {settings.max_network_errors}",
        )

    total_events = (
        len(request.console_logs)
        + len(request.js_exceptions)
        + len(request.network_errors)
    )

    if total_events == 0:
        raise HTTPException(
            status_code=400,
            detail="No error data to analyze. Provide console_logs, js_exceptions, or network_errors.",
        )

    logger.info(f"Analyzing {total_events} events from {request.url}")

    try:
        result = await analyze_errors(request)
        logger.info(f"Analysis complete: severity={result.severity}")
        return result
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/analyze/session", response_model=SessionAnalysisResponse)
async def analyze_session_endpoint(
    request: SessionAnalysisRequest,
    _: User = Depends(require_auth),
) -> SessionAnalysisResponse:
    """Analyze recorded session for test generation."""
    if not request.recorded_requests:
        raise HTTPException(status_code=400, detail="No recorded requests to analyze.")

    logger.info(f"Analyzing session with {len(request.recorded_requests)} requests")

    try:
        result = analyze_session(request.recorded_requests)

        variables = {
            name: DetectedVariable(
                name=name,
                source_request_id=data["source_request_id"],
                source_path=data["source_path"],
                value=data["value"][:50] + "..." if len(data["value"]) > 50 else data["value"],
                used_in=data["used_in"],
            )
            for name, data in result["variables"].items()
        }

        assertions = {
            req_id: [
                RequestAssertion(
                    type=a["type"],
                    path=a.get("path"),
                    expected=str(a["expected"]),
                    description=a["description"],
                )
                for a in assertion_list
            ]
            for req_id, assertion_list in result["assertions"].items()
        }

        logger.info(f"Analysis complete: {result['summary']}")

        return SessionAnalysisResponse(
            variables=variables,
            groups=result["groups"],
            assertions=assertions,
            summary=result["summary"],
        )
    except Exception as e:
        logger.exception(f"Session analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/tickets/generate", response_model=GenerateTicketResponse)
async def create_ticket(
    request: GenerateTicketRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
) -> GenerateTicketResponse:
    """Generate bug ticket from session analysis."""
    query = (
        select(Session)
        .options(selectinload(Session.analysis), selectinload(Session.data))
        .where(Session.id == request.session_id)
    )
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.analysis:
        raise HTTPException(status_code=400, detail="Session has no analysis")

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
        additional_info=request.additional_info,
        format=request.format,
    )

    logger.info(f"Generated {request.format} ticket for session {request.session_id}")

    return GenerateTicketResponse(**ticket)
