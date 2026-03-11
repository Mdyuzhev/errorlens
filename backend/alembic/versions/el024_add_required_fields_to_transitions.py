"""EL024: Add required_fields to status_transitions.

Revision ID: el024_required_fields
Revises: j1q2l3p4a5r6
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = "el024_required_fields"
down_revision = "j1q2l3p4a5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("status_transitions")]
    if "required_fields" not in columns:
        op.add_column(
            "status_transitions",
            sa.Column("required_fields", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("status_transitions", "required_fields")
