"""Notification, GitLabConnection, EntityLink, SavedFilter, TestRun, AutomationRule, AutomationRun models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

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

from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task, TaskType
    from app.models.user import User


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

    # Launch metadata
    launch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pipeline_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="allure")

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
    """Link between entities (article -> article/testcase/task)."""

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


class AutomationRule(Base):
    """Automation rule: event trigger -> actions."""

    __tablename__ = "automation_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    task_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("task_types.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_event: Mapped[str] = mapped_column(String(50))
    trigger_conditions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped[Optional["Project"]] = relationship("Project")
    task_type: Mapped[Optional["TaskType"]] = relationship("TaskType")
    runs: Mapped[list["AutomationRun"]] = relationship(
        "AutomationRun", back_populates="rule", cascade="all, delete-orphan"
    )


class AutomationRun(Base):
    """Single execution of an automation rule."""

    __tablename__ = "automation_runs"
    __table_args__ = (
        Index("ix_automation_runs_status_pipeline", "status", "gitlab_pipeline_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    rule_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("automation_rules.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    trigger_event: Mapped[str] = mapped_column(String(50))
    trigger_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actions_log: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    gitlab_pipeline_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gitlab_connection_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    gitlab_project_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pending_actions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    rule: Mapped[Optional["AutomationRule"]] = relationship("AutomationRule", back_populates="runs")
    task: Mapped[Optional["Task"]] = relationship("Task")
