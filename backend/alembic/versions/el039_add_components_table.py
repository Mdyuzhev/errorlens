"""EL039: Add components table.

Revision ID: el039_components
Revises: el038_sprint_tables
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el039_components"
down_revision = "el038_sprint_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "components",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "lead_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "name", name="uq_component_name_project"),
    )


def downgrade() -> None:
    op.drop_table("components")
