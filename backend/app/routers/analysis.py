"""Analysis and ticket generation endpoints - thin controller."""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.middleware.rate_limit import rate_limit_middleware
from app.models.user import User
from app.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


# Request/Response models
class AnalyzeRequest(BaseModel):
    url: str
    user_agent: str
    console_logs: List[dict] = []
    js_exceptions: List[dict] = []
    network_errors: List[dict] = []
    screenshot: Optional[str] = None
    recording_duration_ms: int = 0


class SessionAnalysisRequest(BaseModel):
    recorded_requests: List[dict]


class GenerateTicketRequest(BaseModel):
    session_id: str
    format: str = "markdown"
    additional_info: Optional[str] = None


class ReanalyzeRequest(BaseModel):
    session_id: str


@router.post("/analyze")
async def analyze(
    request: AnalyzeRequest,
    http_request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    remaining: int = Depends(rate_limit_middleware),
    _: User = Depends(require_auth),
):
    """Analyze captured browser errors using AI."""
    if remaining >= 0:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_day)

    service = AnalysisService(db)

    try:
        result = await service.analyze_errors(
            url=request.url,
            user_agent=request.user_agent,
            console_logs=request.console_logs,
            js_exceptions=request.js_exceptions,
            network_errors=request.network_errors,
            screenshot=request.screenshot,
            recording_duration_ms=request.recording_duration_ms,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/analyze/session")
async def analyze_session(
    request: SessionAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """Analyze recorded session for test generation."""
    service = AnalysisService(db)

    try:
        result = service.analyze_session_requests(request.recorded_requests)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Session analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/analyze/rerun")
async def reanalyze_session(
    request: ReanalyzeRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """Re-run analysis on existing session."""
    service = AnalysisService(db)

    try:
        result = await service.reanalyze_session(request.session_id)
        if not result:
            raise HTTPException(status_code=404, detail="Session not found or has no data")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Re-analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.post("/tickets/generate")
async def create_ticket(
    request: GenerateTicketRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """Generate bug ticket from session analysis."""
    service = AnalysisService(db)

    try:
        result = await service.generate_ticket(
            session_id=request.session_id,
            format=request.format,
            additional_info=request.additional_info,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Ticket generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ticket generation failed: {e}")


@router.get("/analysis/stats")
async def get_analysis_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_auth),
):
    """Get analysis statistics."""
    service = AnalysisService(db)
    return await service.get_analysis_stats()
