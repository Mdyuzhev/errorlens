"""EL046: Add linked_article_ids to test_cases.

Revision ID: el046_linked_articles
Revises: el045_assigned_to
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

revision = "el046_linked_articles"
down_revision = "el045_assigned_to"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_cases",
        sa.Column("linked_article_ids", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_cases", "linked_article_ids")
