"""EL026: Add composite indexes on tasks and sessions tables.

Revision ID: el026_composite_indexes
Revises: el025_automation
Create Date: 2026-03-12
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el026_composite_indexes"
down_revision = "el025_automation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # tasks — most frequent filters
    op.create_index("ix_tasks_project_status", "tasks", ["project_id", "status_id"])
    op.create_index("ix_tasks_project_type", "tasks", ["project_id", "type_id"])
    op.create_index("ix_tasks_project_assignee", "tasks", ["project_id", "assignee_id"])
    op.create_index("ix_tasks_project_priority", "tasks", ["project_id", "priority"])
    op.create_index(
        "ix_tasks_project_created",
        "tasks",
        ["project_id", sa.text("created_at DESC")],
    )
    # sessions
    op.create_index(
        "ix_sessions_project_created",
        "sessions",
        ["project_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_project_created", "sessions")
    op.drop_index("ix_tasks_project_created", "tasks")
    op.drop_index("ix_tasks_project_priority", "tasks")
    op.drop_index("ix_tasks_project_assignee", "tasks")
    op.drop_index("ix_tasks_project_type", "tasks")
    op.drop_index("ix_tasks_project_status", "tasks")
