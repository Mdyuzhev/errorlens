"""Add linked_tc_ids and linked_article_ids to tasks

Revision ID: el064_task_linked
Revises: el063_pechkin
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from alembic import op

revision = "el064_task_linked"
down_revision = "el063_pechkin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("linked_tc_ids", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("linked_article_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "linked_article_ids")
    op.drop_column("tasks", "linked_tc_ids")
