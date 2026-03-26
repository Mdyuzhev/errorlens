"""EL045: Add assigned_to to test_plan_run_results.

Revision ID: el045_assigned_to
Revises: el044_tc_params
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

revision = "el045_assigned_to"
down_revision = "el044_tc_params"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_plan_run_results",
        sa.Column("assigned_to", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_run_result_assigned_to",
        "test_plan_run_results",
        "users",
        ["assigned_to"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_run_result_assigned_to", "test_plan_run_results", type_="foreignkey")
    op.drop_column("test_plan_run_results", "assigned_to")
