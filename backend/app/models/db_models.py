"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate UUID string for primary keys."""
    return str(uuid.uuid4())


# ============= Multi-tenancy Models =============


class Project(Base):
    """Project for multi-tenancy grouping."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Owner
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Plan (free/pro)
    plan: Mapped[str] = mapped_column(String(20), default="free")

    # Settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    folders: Mapped[List["Folder"]] = relationship(
        "Folder", back_populates="project", cascade="all, delete-orphan"
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="project", cascade="all, delete-orphan"
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase", back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    articles: Mapped[List["Article"]] = relationship(
        "Article", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project {self.slug}>"


class Folder(Base):
    """Folder within a project for organizing test cases."""

    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Parent project
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )

    # Parent folder (for nested structure)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="folders")
    parent: Mapped[Optional["Folder"]] = relationship(
        "Folder", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Folder"]] = relationship(
        "Folder", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"


class ProjectMember(Base):
    """Project membership (many-to-many User <-> Project)."""

    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Foreign keys
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Role within project
    role: Mapped[str] = mapped_column(String(20), default="member")  # owner, admin, member, viewer

    # Who added this member
    added_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<ProjectMember {self.user_id} in {self.project_id}>"


class Session(Base):
    """Recorded browser session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    url: Mapped[str] = mapped_column(String(2048))
    user_agent: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    recording_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    record_mode: Mapped[str] = mapped_column(
        String(20), default="errors"
    )  # 'errors' or 'all'

    # Multi-tenancy
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # External integrations
    testit_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    testit_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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
    screenshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_events_count: Mapped[int] = mapped_column(Integer, default=0)

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<AnalysisResult {self.severity} for {self.session_id[:8]}...>"


class TestCase(Base):
    """Test case entity for test management."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    postconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    automation_status: Mapped[str] = mapped_column(String(20), default="Manual")

    # Multi-tenancy
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Linking
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    folder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=list)

    # Steps as JSON array
    steps: Mapped[dict] = mapped_column(JSON, default=list)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # External links
    external_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="test_cases")


class Task(Base):
    """Task for internal task tracking."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status & Priority
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    # Multi-tenancy
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Linking
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    testcase_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True
    )

    # Assignment
    assignee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    labels: Mapped[dict] = mapped_column(JSON, default=list)

    # Dates
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # External integration
    jira_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    github_issue: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks")


class Article(Base):
    """Knowledge base article."""

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    content: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Multi-tenancy
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Organization
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=list)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # Metadata
    author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Stats
    views: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="articles")


class TestRun(Base):
    """Test execution result."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    test_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Results
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)

    # Detailed results as JSON
    results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
