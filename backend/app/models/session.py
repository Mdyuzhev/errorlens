"""Session, SessionData, AnalysisResult models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class Session(Base):
    """Recorded browser session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    url: Mapped[str] = mapped_column(String(2048))
    user_agent: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    recording_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    record_mode: Mapped[str] = mapped_column(String(20), default="errors")  # 'errors' or 'all'

    # Multi-tenancy
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # External integrations
    testit_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    testit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="sessions")
    data: Mapped[Optional["SessionData"]] = relationship(
        "SessionData", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    analysis: Mapped[Optional["AnalysisResult"]] = relationship(
        "AnalysisResult", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session {self.id[:8]}... {self.url[:50]}>"


class SessionData(Base):
    """Raw captured data from browser session."""

    __tablename__ = "session_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE")
    )

    # JSON fields for captured data
    console_logs: Mapped[dict] = mapped_column(JSON, default=list)
    network_errors: Mapped[dict] = mapped_column(JSON, default=list)
    js_exceptions: Mapped[dict] = mapped_column(JSON, default=list)
    recorded_requests: Mapped[dict] = mapped_column(JSON, default=list)

    # Screenshot (base64 encoded)
    screenshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="data")

    def __repr__(self) -> str:
        return f"<SessionData for {self.session_id[:8]}...>"


class AnalysisResult(Base):
    """AI analysis result for a session."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE")
    )

    # Analysis fields
    summary: Mapped[str] = mapped_column(Text)
    probable_cause: Mapped[str] = mapped_column(Text)
    suggested_fix: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))  # low, medium, high, critical
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_events_count: Mapped[int] = mapped_column(Integer, default=0)

    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<AnalysisResult {self.severity} for {self.session_id[:8]}...>"
