"""SQLAlchemy database models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.user import User

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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

    # Project key for human-readable IDs (e.g. "EL")
    key: Mapped[str | None] = mapped_column(String(4), unique=True, index=True, nullable=True)
    entity_counter: Mapped[int] = mapped_column(Integer, default=0)

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
    test_plans: Mapped[list["TestPlan"]] = relationship(
        "TestPlan", back_populates="project", cascade="all, delete-orphan"
    )
    task_types: Mapped[list["TaskType"]] = relationship(
        "TaskType", back_populates="project", cascade="all, delete-orphan"
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
    human_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
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


class TaskType(Base):
    """Task type (Bug, Task, Story, Epic, Release) - project-level."""

    __tablename__ = "task_types"
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_task_type_project_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(30))
    icon: Mapped[str] = mapped_column(String(30))
    color: Mapped[str] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="task_types")
    statuses: Mapped[list["TaskStatus"]] = relationship(
        "TaskStatus", back_populates="task_type", cascade="all, delete-orphan"
    )


class TaskStatus(Base):
    """Task status - per task type, project-level."""

    __tablename__ = "task_statuses"
    __table_args__ = (
        UniqueConstraint("project_id", "task_type_id", "slug", name="uq_task_status_type_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    task_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task_types.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    slug: Mapped[str] = mapped_column(String(30))
    color: Mapped[str] = mapped_column(String(7))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    task_type: Mapped["TaskType"] = relationship("TaskType", back_populates="statuses")


class StatusTransition(Base):
    """Allowed transition between task statuses."""

    __tablename__ = "status_transitions"
    __table_args__ = (
        UniqueConstraint("from_status_id", "to_status_id", name="uq_status_transition"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    from_status_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task_statuses.id", ondelete="CASCADE"), index=True
    )
    to_status_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("task_statuses.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    required_fields: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)

    # Relationships
    from_status: Mapped["TaskStatus"] = relationship("TaskStatus", foreign_keys=[from_status_id])
    to_status: Mapped["TaskStatus"] = relationship("TaskStatus", foreign_keys=[to_status_id])


class Task(Base):
    """Task for internal task tracking."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    human_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status & Priority (old string status kept for backward compat — remove in EL020)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    priority: Mapped[str] = mapped_column(String(20), default="medium")

    # New FK-based type and status
    type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("task_types.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("task_statuses.id", ondelete="SET NULL"), nullable=True, index=True
    )

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

    # Assignment (old string field kept for backward compat — remove in EL020)
    assignee: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assignee_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reporter_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    labels: Mapped[dict] = mapped_column(JSON, default=list)

    # Severity & Environment
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Time tracking
    estimated_hours: Mapped[float | None] = mapped_column(nullable=True)
    spent_hours: Mapped[float | None] = mapped_column(nullable=True)

    # Hierarchy (max depth 4)
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )

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
    task_type: Mapped[Optional["TaskType"]] = relationship("TaskType")
    task_status: Mapped[Optional["TaskStatus"]] = relationship("TaskStatus")
    assignee_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assignee_id], lazy="joined"
    )
    reporter: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reporter_id], lazy="joined"
    )
    parent: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side="Task.id", foreign_keys=[parent_id]
    )
    children: Mapped[list["Task"]] = relationship(
        "Task", foreign_keys=[parent_id], lazy="selectin",
        overlaps="parent",
    )
    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="task", cascade="all, delete-orphan"
    )
    activities: Mapped[list["TaskActivity"]] = relationship(
        "TaskActivity", back_populates="task", cascade="all, delete-orphan"
    )


class TaskComment(Base):
    """Comment on a task."""

    __tablename__ = "task_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    author: Mapped[Optional["User"]] = relationship("User", lazy="joined")


class TaskActivity(Base):
    """Append-only activity log for a task."""

    __tablename__ = "task_activities"
    __table_args__ = (
        Index("ix_task_activities_task_created", "task_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(30))
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="activities")
    actor: Mapped[Optional["User"]] = relationship("User", lazy="joined")


class TaskRelation(Base):
    """Semantic relation between tasks (blocks, duplicates, relates_to)."""

    __tablename__ = "task_relations"
    __table_args__ = (
        UniqueConstraint("source_task_id", "target_task_id", "relation_type", name="uq_task_relation"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    target_task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    source_task: Mapped["Task"] = relationship("Task", foreign_keys=[source_task_id])
    target_task: Mapped["Task"] = relationship("Task", foreign_keys=[target_task_id])


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
    human_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
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


# ============= Test Plans =============


class TestPlan(Base):
    """Test plan — container of test cases for targeted testing."""

    __tablename__ = "test_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    human_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # Multi-tenancy
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )

    # Audit
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="test_plans")
    cases: Mapped[list["TestPlanCase"]] = relationship(
        "TestPlanCase", back_populates="plan", cascade="all, delete-orphan"
    )
    runs: Mapped[list["TestPlanRun"]] = relationship(
        "TestPlanRun", back_populates="plan", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestPlan {self.name}>"


class TestPlanCase(Base):
    """Link between test plan and test case."""

    __tablename__ = "test_plan_cases"
    __table_args__ = (
        UniqueConstraint("plan_id", "testcase_id", name="uq_plan_case"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_plans.id", ondelete="CASCADE"), index=True
    )
    testcase_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_cases.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    plan: Mapped["TestPlan"] = relationship("TestPlan", back_populates="cases")
    testcase: Mapped["TestCase"] = relationship("TestCase")

    def __repr__(self) -> str:
        return f"<TestPlanCase plan={self.plan_id} tc={self.testcase_id}>"


class TestPlanRun(Base):
    """Concrete execution of a test plan."""

    __tablename__ = "test_plan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    plan_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_plans.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")

    # Who started
    started_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Counters
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    blocked: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    plan: Mapped["TestPlan"] = relationship("TestPlan", back_populates="runs")
    results: Mapped[list["TestPlanRunResult"]] = relationship(
        "TestPlanRunResult", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestPlanRun {self.name}>"


class TestPlanRunResult(Base):
    """Result for a single test case in a run."""

    __tablename__ = "test_plan_run_results"
    __table_args__ = (
        UniqueConstraint("run_id", "testcase_id", name="uq_run_result"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_plan_runs.id", ondelete="CASCADE"), index=True
    )
    testcase_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    run: Mapped["TestPlanRun"] = relationship("TestPlanRun", back_populates="results")
    testcase: Mapped[Optional["TestCase"]] = relationship("TestCase")

    def __repr__(self) -> str:
        return f"<TestPlanRunResult run={self.run_id} tc={self.testcase_id} status={self.status}>"


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


class Notification(Base):
    """User notification from domain events."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_notification_user_event"),
        Index("ix_notifications_user_unread", "user_id", "is_read", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str] = mapped_column(String(36), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Notification {self.type} for {self.user_id[:8]}>"


# ============= GitLab Integration =============


class GitLabConnection(Base):
    """GitLab connection for CI/CD integration."""

    __tablename__ = "gitlab_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(500))
    token_encrypted: Mapped[str] = mapped_column(Text)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_check_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )

    # Relationships
    organization: Mapped["Project"] = relationship("Project")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<GitLabConnection {self.name} ({self.url})>"


class EntityLink(Base):
    """Link between entities (article → article/testcase/task)."""

    __tablename__ = "entity_links"
    __table_args__ = (
        UniqueConstraint("source_id", "target_type", "target_id", name="uq_entity_link_source_target"),
        Index("ix_entity_links_source_id", "source_id"),
        Index("ix_entity_links_target", "target_type", "target_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("articles.id", ondelete="CASCADE")
    )
    target_type: Mapped[str] = mapped_column(String(20))  # article, testcase, task
    target_id: Mapped[str] = mapped_column(String(36))
    link_type: Mapped[str] = mapped_column(String(20))  # verifies, related

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SavedFilter(Base):
    """User-saved JQL filter."""

    __tablename__ = "saved_filters"
    __table_args__ = (
        UniqueConstraint("owner_id", "project_id", "name", name="uq_saved_filter_owner_project_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    jql: Mapped[str] = mapped_column(Text)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
