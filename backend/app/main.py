"""ErrorLens API - FastAPI entrypoint."""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.analyzer import analyze_errors
from app.config import settings
from app.models import AnalyzeRequest, AnalyzeResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ErrorLens API",
    description="AI-powered error analysis for QA engineers",
    version=settings.version,
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
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze captured browser errors using AI.

    Accepts console logs, network errors, and JS exceptions,
    returns structured analysis with probable cause and fix suggestions.
    """
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
