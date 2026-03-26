"""EL040: Add issue_custom_fields and issue_custom_values tables.

Revision ID: el040_custom_fields
Revises: el039_components
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el040_custom_fields"
down_revision = "el039_components"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issue_custom_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "task_type_id",
            sa.String(36),
            sa.ForeignKey("task_types.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "issue_custom_values",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "issue_id",
            sa.String(36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "field_id",
            sa.String(36),
            sa.ForeignKey("issue_custom_fields.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("value", sa.JSON, nullable=True),
        sa.UniqueConstraint("issue_id", "field_id", name="uq_custom_value"),
    )


def downgrade() -> None:
    op.drop_table("issue_custom_values")
    op.drop_table("issue_custom_fields")
