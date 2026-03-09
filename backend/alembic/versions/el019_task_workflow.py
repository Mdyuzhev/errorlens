"""EL019: Add task workflow tables and new task fields.

Revision ID: el019_workflow
Revises: n1o2t3i4f5y6
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = "el019_workflow"
down_revision = "n1o2t3i4f5y6"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    insp = inspect(conn)
    return name in insp.get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    insp = inspect(conn)
    if table not in insp.get_table_names():
        return False
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def upgrade() -> None:
    conn = op.get_bind()

    # ---- Task Types ----
    if not _table_exists(conn, "task_types"):
        op.create_table(
            "task_types",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("slug", sa.String(30), nullable=False),
            sa.Column("icon", sa.String(30), nullable=False),
            sa.Column("color", sa.String(7), nullable=False),
            sa.Column("sort_order", sa.Integer, default=0),
            sa.Column("is_active", sa.Boolean, default=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint("project_id", "slug", name="uq_task_type_project_slug"),
        )

    # ---- Task Statuses ----
    if not _table_exists(conn, "task_statuses"):
        op.create_table(
            "task_statuses",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("task_type_id", sa.String(36), sa.ForeignKey("task_types.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("slug", sa.String(30), nullable=False),
            sa.Column("color", sa.String(7), nullable=False),
            sa.Column("sort_order", sa.Integer, default=0),
            sa.Column("is_initial", sa.Boolean, default=False),
            sa.Column("is_final", sa.Boolean, default=False),
            sa.UniqueConstraint("project_id", "task_type_id", "slug", name="uq_task_status_type_slug"),
        )

    # ---- Status Transitions ----
    if not _table_exists(conn, "status_transitions"):
        op.create_table(
            "status_transitions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("from_status_id", sa.String(36), sa.ForeignKey("task_statuses.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("to_status_id", sa.String(36), sa.ForeignKey("task_statuses.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.UniqueConstraint("from_status_id", "to_status_id", name="uq_status_transition"),
        )

    # ---- Task Comments ----
    if not _table_exists(conn, "task_comments"):
        op.create_table(
            "task_comments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("is_edited", sa.Boolean, default=False),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=True),
        )

    # ---- Task Activities ----
    if not _table_exists(conn, "task_activities"):
        op.create_table(
            "task_activities",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("action_type", sa.String(30), nullable=False),
            sa.Column("field_name", sa.String(50), nullable=True),
            sa.Column("old_value", sa.JSON, nullable=True),
            sa.Column("new_value", sa.JSON, nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("ix_task_activities_task_created", "task_activities", ["task_id", "created_at"])

    # ---- Task Relations ----
    if not _table_exists(conn, "task_relations"):
        op.create_table(
            "task_relations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("source_task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("target_task_id", sa.String(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("relation_type", sa.String(30), nullable=False),
            sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint("source_task_id", "target_task_id", "relation_type", name="uq_task_relation"),
        )

    # ---- New columns on tasks table ----
    new_columns = [
        ("type_id", sa.String(36), {"nullable": True}),
        ("status_id", sa.String(36), {"nullable": True}),
        ("assignee_id", sa.String(36), {"nullable": True}),
        ("reporter_id", sa.String(36), {"nullable": True}),
        ("severity", sa.String(20), {"nullable": True}),
        ("environment", sa.String(30), {"nullable": True}),
        ("estimated_hours", sa.Float, {"nullable": True}),
        ("spent_hours", sa.Float, {"nullable": True}),
        ("parent_id", sa.String(36), {"nullable": True}),
    ]

    for col_name, col_type, kwargs in new_columns:
        if not _column_exists(conn, "tasks", col_name):
            op.add_column("tasks", sa.Column(col_name, col_type, **kwargs))

    # Add foreign keys for new columns (PostgreSQL)
    # FKs are added separately to avoid issues with column creation order
    try:
        op.create_foreign_key("fk_tasks_type_id", "tasks", "task_types", ["type_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass
    try:
        op.create_foreign_key("fk_tasks_status_id", "tasks", "task_statuses", ["status_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass
    try:
        op.create_foreign_key("fk_tasks_assignee_id", "tasks", "users", ["assignee_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass
    try:
        op.create_foreign_key("fk_tasks_reporter_id", "tasks", "users", ["reporter_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass
    try:
        op.create_foreign_key("fk_tasks_parent_id", "tasks", "tasks", ["parent_id"], ["id"], ondelete="SET NULL")
    except Exception:
        pass

    # Indexes for new columns
    try:
        op.create_index("ix_tasks_type_id", "tasks", ["type_id"])
    except Exception:
        pass
    try:
        op.create_index("ix_tasks_status_id", "tasks", ["status_id"])
    except Exception:
        pass
    try:
        op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"])
    except Exception:
        pass
    try:
        op.create_index("ix_tasks_parent_id", "tasks", ["parent_id"])
    except Exception:
        pass


def downgrade() -> None:
    # Drop new columns from tasks
    for col in ["parent_id", "spent_hours", "estimated_hours", "environment", "severity", "reporter_id", "assignee_id", "status_id", "type_id"]:
        try:
            op.drop_column("tasks", col)
        except Exception:
            pass

    # Drop new tables in reverse order
    for table in ["task_relations", "task_activities", "task_comments", "status_transitions", "task_statuses", "task_types"]:
        op.drop_table(table)
