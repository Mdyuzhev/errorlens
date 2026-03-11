"""Add saved_filters table for JQL.

Revision ID: j1q2l3p4a5r6
Revises: n1o2t3i4f5y6
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = "j1q2l3p4a5r6"
down_revision = "n1o2t3i4f5y6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    if "saved_filters" not in tables:
        op.create_table(
            "saved_filters",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("jql", sa.Text, nullable=False),
            sa.Column("is_shared", sa.Boolean, default=False),
            sa.Column("created_at", sa.DateTime, default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=True),
            sa.UniqueConstraint("owner_id", "project_id", "name", name="uq_saved_filter_owner_project_name"),
        )


def downgrade() -> None:
    op.drop_table("saved_filters")
