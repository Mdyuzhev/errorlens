"""add entity_links table

Revision ID: f1a2b3c4d5e6
Revises: e8a09aa606cf
Create Date: 2026-03-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e8a09aa606cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entity_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.Column("link_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_entity_links_source_id", "entity_links", ["source_id"])
    op.create_index("ix_entity_links_target", "entity_links", ["target_type", "target_id"])
    op.create_unique_constraint(
        "uq_entity_link_source_target", "entity_links", ["source_id", "target_type", "target_id"]
    )


def downgrade() -> None:
    op.drop_table("entity_links")
