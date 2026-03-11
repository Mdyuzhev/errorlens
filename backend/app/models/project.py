"""Project, ProjectMember, Folder models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.article import Article, ArticleFolder
    from app.models.session import Session
    from app.models.task import Task, TaskType
    from app.models.testcase import TestCase, TestCaseFolder
    from app.models.testplan import TestPlan
    from app.models.user import User


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
