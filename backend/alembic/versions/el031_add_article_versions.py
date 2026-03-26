"""EL031: Add article_versions table for version history.

Revision ID: el031_article_versions
Revises: el026_composite_indexes
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = "el031_article_versions"
down_revision = "el026_composite_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = inspector.get_table_names()

    if "article_versions" not in existing:
        op.create_table(
            "article_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "article_id", sa.String(36),
                sa.ForeignKey("articles.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column(
                "saved_by", sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at", sa.DateTime,
                server_default=sa.func.now(), nullable=False,
            ),
        )
        op.create_index(
            "ix_article_versions_article_id",
            "article_versions",
            ["article_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_article_versions_article_id", table_name="article_versions")
    op.drop_table("article_versions")
