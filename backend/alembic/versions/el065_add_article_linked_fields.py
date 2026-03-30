"""EL065: Add linked_issue_ids, linked_testcase_ids to articles.

Revision ID: el065_article_links
Revises: el064_task_linked
Create Date: 2026-03-30
"""

import sqlalchemy as sa
from alembic import op

revision = "el065_article_links"
down_revision = "el064_task_linked"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("linked_issue_ids", sa.JSON(), nullable=True))
    op.add_column("articles", sa.Column("linked_testcase_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "linked_testcase_ids")
    op.drop_column("articles", "linked_issue_ids")
