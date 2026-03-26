"""EL044: Add parameters, linked_issue_ids to test_cases.

Revision ID: el044_tc_params
Revises: el043_task_fields
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

revision = "el044_tc_params"
down_revision = "el043_task_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_cases", sa.Column("parameters", sa.JSON(), nullable=True))
    op.add_column("test_cases", sa.Column("linked_issue_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("test_cases", "linked_issue_ids")
    op.drop_column("test_cases", "parameters")
