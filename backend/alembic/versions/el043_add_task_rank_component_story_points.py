"""EL043: Add rank, component_id, story_points columns to tasks table.

Revision ID: el043_task_fields
Revises: el042_work_logs
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el043_task_fields"
down_revision = "el042_work_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("rank", sa.Integer, nullable=False, server_default="0"))
    op.add_column("tasks", sa.Column("component_id", sa.String(36), nullable=True))
    op.add_column("tasks", sa.Column("story_points", sa.Integer, nullable=True))

    op.create_foreign_key(
        "fk_tasks_component_id", "tasks", "components", ["component_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tasks_component_id", "tasks", ["component_id"])
    op.create_index("ix_tasks_rank", "tasks", ["rank"])


def downgrade() -> None:
    op.drop_index("ix_tasks_rank", "tasks")
    op.drop_index("ix_tasks_component_id", "tasks")
    op.drop_constraint("fk_tasks_component_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "story_points")
    op.drop_column("tasks", "component_id")
    op.drop_column("tasks", "rank")
