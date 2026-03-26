"""EL041: Add issue_attachments table.

Revision ID: el041_issue_attachments
Revises: el040_custom_fields
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el041_issue_attachments"
down_revision = "el040_custom_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issue_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "issue_id",
            sa.String(36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("object_key", sa.String(500), nullable=False, unique=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column(
            "uploaded_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("issue_attachments")
