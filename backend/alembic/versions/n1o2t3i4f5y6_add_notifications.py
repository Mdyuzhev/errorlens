"""Add notifications table.

Revision ID: n1o2t3i4f5y6
Revises: h1i2j3k4l5m6
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = "n1o2t3i4f5y6"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if "notifications" in inspector.get_table_names():
        return

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_id", sa.String(36), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("entity_type", sa.String(30), nullable=True),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("is_read", sa.Boolean, default=False, nullable=False),
        sa.Column(
            "created_at", sa.DateTime, server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_unique_constraint(
        "uq_notification_user_event", "notifications", ["user_id", "event_id"]
    )

    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_constraint("uq_notification_user_event", "notifications", type_="unique")
    op.drop_table("notifications")
