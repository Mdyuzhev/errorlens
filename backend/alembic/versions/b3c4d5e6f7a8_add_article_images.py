"""Add article_images table.

Revision ID: b3c4d5e6f7a8
Revises: 02eb2a85b4b4
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "b3c4d5e6f7a8"
down_revision = "02eb2a85b4b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_images",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("object_key", sa.String(500), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "article_id",
            sa.String(36),
            sa.ForeignKey("articles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("article_images")
