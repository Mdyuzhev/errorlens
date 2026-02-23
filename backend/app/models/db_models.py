"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate UUID string for primary keys."""
    return str(uuid.uuid4())


# ============= Multi-tenancy Models =============


class Project(Base):
    """Project for multi-tenancy grouping."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Owner
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))

    # Plan (free/pro)
    plan: Mapped[str] = mapped_column(String(20), default="free")

    # Settings
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    folders: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="project", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="project", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase", back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan"
    )
    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="project", cascade="all, delete-orphan"
    )
    article_folders: Mapped[list["ArticleFolder"]] = relationship(
        "ArticleFolder", back_populates="project", cascade="all, delete-orphan"
    )
    testcase_folders: Mapped[list["TestCaseFolder"]] = relationship(
        "TestCaseFolder", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project {self.slug}>"


class Folder(Base):
    """Folder within a project for organizing test cases."""

    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Parent project
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )

    # Parent folder (for nested structure)
    parent_id: Mapped[str | None] = mapped_column(
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
    children: Mapped[list["Folder"]] = relationship(
        "Folder", back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"


class ProjectMember(Base):
    """Project membership (many-to-many User <-> Project)."""

    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Foreign keys
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"))

    # Role within project
    role: Mapped[str] = mapped_column(String(20), default="member")  # owner, admin, member, viewer

    # Who added this member
    added_by_id: Mapped[str | None] = mapped_column(
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


class TestCase(Base):
    """Test case entity for test management."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    preconditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    postconditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    automation_status: Mapped[str] = mapped_column(String(20), default="Manual")

    # Multi-tenancy
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Linking
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    folder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    folder_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("testcase_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tags: Mapped[dict] = mapped_column(JSON, default=list)

    # Steps as JSON array
    steps: Mapped[dict] = mapped_column(JSON, default=list)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # External links
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="test_cases")
    testcase_folder: Mapped[Optional["TestCaseFolder"]] = relationship(
        "TestCaseFolder", back_populates="test_cases"
    )


class Task(Base):
    """Task for internal task tracking."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status & Priority
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    # Multi-tenancy
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Linking
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    testcase_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True
    )

    # Assignment
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    labels: Mapped[dict] = mapped_column(JSON, default=list)

    # Dates
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # External integration
    jira_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    github_issue: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="tasks")


class TestCaseFolder(Base):
    """Folder for organizing test cases in a tree hierarchy (max depth 3)."""

    __tablename__ = "testcase_folders"
    __table_args__ = (
        UniqueConstraint("name", "parent_id", "project_id", name="uq_testcase_folder_name_parent_project"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200))

    # Parent folder (self-reference)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("testcase_folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Multi-tenancy
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="testcase_folders")
    parent: Mapped[Optional["TestCaseFolder"]] = relationship(
        "TestCaseFolder", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["TestCaseFolder"]] = relationship(
        "TestCaseFolder", back_populates="parent", cascade="all, delete-orphan"
    )
    test_cases: Mapped[list["TestCase"]] = relationship(
        "TestCase", back_populates="testcase_folder"
    )

    def __repr__(self) -> str:
        return f"<TestCaseFolder {self.name}>"


class ArticleFolder(Base):
    """Folder for organizing articles in a tree hierarchy (max depth 3)."""

    __tablename__ = "article_folders"
    __table_args__ = (
        UniqueConstraint("name", "parent_id", "project_id", name="uq_article_folder_name_parent_project"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200))

    # Parent folder (self-reference)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("article_folders.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Multi-tenancy
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="article_folders")
    parent: Mapped[Optional["ArticleFolder"]] = relationship(
        "ArticleFolder", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["ArticleFolder"]] = relationship(
        "ArticleFolder", back_populates="parent", cascade="all, delete-orphan"
    )
    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="article_folder"
    )

    def __repr__(self) -> str:
        return f"<ArticleFolder {self.name}>"


class Article(Base):
    """Knowledge base article."""

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(500))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    content: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Multi-tenancy
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )

    # Folder (tree structure)
    folder_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("article_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Organization
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=list)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # Metadata
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Stats
    views: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="articles")
    article_folder: Mapped[Optional["ArticleFolder"]] = relationship(
        "ArticleFolder", back_populates="articles"
    )
    images: Mapped[list["ArticleImage"]] = relationship(
        "ArticleImage", back_populates="article"
    )


class ArticleImage(Base):
    """Image attached to an article, stored in S3/MinIO."""

    __tablename__ = "article_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    object_key: Mapped[str] = mapped_column(String(500), unique=True)
    original_filename: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Multi-tenancy
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )

    # Link to article (optional — image can be orphan before insertion)
    article_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )

    # Audit
    uploaded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    article: Mapped[Optional["Article"]] = relationship("Article", back_populates="images")

    def __repr__(self) -> str:
        return f"<ArticleImage {self.object_key}>"


class TestRun(Base):
    """Test execution result."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    test_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Results
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)

    # Detailed results as JSON
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
