"""Task, TaskType, TaskStatus, StatusTransition, TaskComment, TaskActivity, TaskRelation models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.user import User


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
