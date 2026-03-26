"""EL042: Add work_logs table.

Revision ID: el042_work_logs
Revises: el041_issue_attachments
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el042_work_logs"
down_revision = "el041_issue_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "issue_id",
            sa.String(36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("hours", sa.Float, nullable=False),
        sa.Column("log_date", sa.DateTime, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("work_logs")
