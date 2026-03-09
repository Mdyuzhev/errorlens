"""Add project key and human_id fields

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-03-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def has_column(table_name: str, column_name: str) -> bool:
    """Check if column exists in table."""
    bind = op.get_bind()
    insp = inspect(bind)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Projects: key + entity_counter
    if not has_column("projects", "key"):
        op.add_column("projects", sa.Column("key", sa.String(4), nullable=True))
        op.create_unique_constraint("uq_projects_key", "projects", ["key"])
        op.create_index("ix_projects_key", "projects", ["key"])

    if not has_column("projects", "entity_counter"):
        op.add_column(
            "projects",
            sa.Column("entity_counter", sa.Integer(), server_default="0", nullable=False),
        )

    # human_id for entities
    for table in ("test_cases", "tasks", "articles"):
        if not has_column(table, "human_id"):
            op.add_column(table, sa.Column("human_id", sa.String(20), nullable=True))
            op.create_index(f"ix_{table}_human_id", table, ["human_id"])


def downgrade() -> None:
    for table in ("articles", "tasks", "test_cases"):
        op.drop_index(f"ix_{table}_human_id", table_name=table)
        op.drop_column(table, "human_id")

    op.drop_index("ix_projects_key", table_name="projects")
    op.drop_constraint("uq_projects_key", "projects", type_="unique")
    op.drop_column("projects", "entity_counter")
    op.drop_column("projects", "key")
