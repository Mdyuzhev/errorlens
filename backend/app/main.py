"""ErrorLens API - FastAPI entrypoint."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.analyzer import analyze_errors
from app.config import settings
from app.database import init_db
from app.middleware.rate_limit import rate_limit_middleware
from app.models_pydantic import (
    AnalyzeRequest,
    AnalyzeResponse,
    DetectedVariable,
    ExportPostmanRequest,
    ExportPostmanResponse,
    RequestAssertion,
    SessionAnalysisRequest,
    SessionAnalysisResponse,
)
from app.postman_generator import generate_postman_collection
from app.session_analyzer import analyze_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown: cleanup if needed
    logger.info("Shutting down...")


app = FastAPI(
    title="ErrorLens API",
    description="AI-powered error analysis for QA engineers",
    version=settings.version,
    lifespan=lifespan,
)

# CORS: allow all origins (bookmarklet runs on any domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": settings.version}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest,
    http_request: Request,
    response: Response,
    remaining: int = Depends(rate_limit_middleware),
) -> AnalyzeResponse:
    """
    Analyze captured browser errors using AI.

    Accepts console logs, network errors, and JS exceptions,
    returns structured analysis with probable cause and fix suggestions.
    """
    # Add rate limit header
    if remaining >= 0:
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_per_day)

    # Validate payload limits
    if len(request.console_logs) > settings.max_console_logs:
        raise HTTPException(
            status_code=400,
            detail=f"Превышен лимит console_logs: максимум {settings.max_console_logs}",
        )
    if len(request.network_errors) > settings.max_network_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Превышен лимит network_errors: максимум {settings.max_network_errors}",
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


@app.post("/export/postman", response_model=ExportPostmanResponse)
async def export_postman(request: ExportPostmanRequest) -> ExportPostmanResponse:
    """
    Generate Postman Collection from recorded HTTP exchanges.

    Converts recorded requests/responses into a Postman Collection v2.1
    with optional test assertions and environment variables.
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to export.",
        )

    logger.info(f"Generating Postman collection from {len(request.recorded_requests)} requests")

    try:
        result = generate_postman_collection(request)
        logger.info(f"Generated collection with {result.requests_count} items")
        return result
    except Exception as e:
        logger.exception(f"Postman export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@app.post("/analyze/session", response_model=SessionAnalysisResponse)
async def analyze_session_endpoint(request: SessionAnalysisRequest) -> SessionAnalysisResponse:
    """
    Analyze recorded session for test generation.

    Detects variables (tokens, IDs), groups requests by scenario,
    and extracts assertions for each request.
    """
    if not request.recorded_requests:
        raise HTTPException(
            status_code=400,
            detail="No recorded requests to analyze.",
        )

    logger.info(f"Analyzing session with {len(request.recorded_requests)} requests")

    try:
        result = analyze_session(request.recorded_requests)

        # Convert to response model
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
