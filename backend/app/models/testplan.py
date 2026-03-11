"""TestPlan, TestPlanCase, TestPlanRun, TestPlanRunResult models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.testcase import TestCase


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
