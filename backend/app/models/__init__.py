"""Models package - exports both Pydantic and SQLAlchemy models."""

# Re-export Pydantic models from original location
# Export SQLAlchemy models
from app.models.db_models import AnalysisResult, Session, SessionData
from app.models.user import User
from app.models_pydantic import (
    AnalyzeRequest,
    AnalyzeResponse,
    ConsoleLogEntry,
    DetectedVariable,
    ExportPostmanRequest,
    ExportPostmanResponse,
    JSException,
    NetworkError,
    RecordedRequest,
    RequestAssertion,
    SessionAnalysisRequest,
    SessionAnalysisResponse,
)

__all__ = [
    # Pydantic models
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ConsoleLogEntry",
    "DetectedVariable",
    "ExportPostmanRequest",
    "ExportPostmanResponse",
    "JSException",
    "NetworkError",
    "RecordedRequest",
    "RequestAssertion",
    "SessionAnalysisRequest",
    "SessionAnalysisResponse",
    # SQLAlchemy models
    "Session",
    "SessionData",
    "AnalysisResult",
    "User",
]
