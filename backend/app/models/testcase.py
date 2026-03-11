"""TestCase, TestCaseFolder models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


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
