"""Add test plans tables

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-03-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "h1i2j3k4l5m6"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def has_table(table_name: str) -> bool:
    """Check if table exists."""
    bind = op.get_bind()
    insp = inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    if not has_table("test_plans"):
        op.create_table(
            "test_plans",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("human_id", sa.String(20), nullable=True, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(20), server_default="draft", nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if not has_table("test_plan_cases"):
        op.create_table(
            "test_plan_cases",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("plan_id", sa.String(36), sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("testcase_id", sa.String(36), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("added_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("plan_id", "testcase_id", name="uq_plan_case"),
        )

    if not has_table("test_plan_runs"):
        op.create_table(
            "test_plan_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("plan_id", sa.String(36), sa.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("status", sa.String(20), server_default="in_progress", nullable=False),
            sa.Column("started_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("total", sa.Integer(), server_default="0", nullable=False),
            sa.Column("passed", sa.Integer(), server_default="0", nullable=False),
            sa.Column("failed", sa.Integer(), server_default="0", nullable=False),
            sa.Column("blocked", sa.Integer(), server_default="0", nullable=False),
            sa.Column("skipped", sa.Integer(), server_default="0", nullable=False),
        )

    if not has_table("test_plan_run_results"):
        op.create_table(
            "test_plan_run_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("run_id", sa.String(36), sa.ForeignKey("test_plan_runs.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("testcase_id", sa.String(36), sa.ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("status", sa.String(20), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("error_details", sa.Text(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.Column("executed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("run_id", "testcase_id", name="uq_run_result"),
        )


def downgrade() -> None:
    op.drop_table("test_plan_run_results")
    op.drop_table("test_plan_runs")
    op.drop_table("test_plan_cases")
    op.drop_table("test_plans")
