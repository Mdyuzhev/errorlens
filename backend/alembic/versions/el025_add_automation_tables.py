"""EL025: Add automation_rules and automation_runs tables.

Revision ID: el025_automation
Revises: el024_required_fields
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = "el025_automation"
down_revision = "el024_required_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = inspector.get_table_names()

    if "automation_rules" not in existing:
        op.create_table(
            "automation_rules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "project_id", sa.String(36),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False, index=True,
            ),
            sa.Column(
                "task_type_id", sa.String(36),
                sa.ForeignKey("task_types.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("is_active", sa.Boolean, default=True, nullable=False),
            sa.Column("trigger_event", sa.String(50), nullable=False),
            sa.Column("trigger_conditions", sa.JSON, nullable=True),
            sa.Column("actions", sa.JSON, nullable=False),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime, nullable=True),
        )

    if "automation_runs" not in existing:
        op.create_table(
            "automation_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "rule_id", sa.String(36),
                sa.ForeignKey("automation_rules.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "task_id", sa.String(36),
                sa.ForeignKey("tasks.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("status", sa.String(20), nullable=False, default="pending"),
            sa.Column("trigger_event", sa.String(50), nullable=False),
            sa.Column("trigger_payload", sa.JSON, nullable=True),
            sa.Column("actions_log", sa.JSON, nullable=True),
            sa.Column("gitlab_pipeline_id", sa.Integer, nullable=True),
            sa.Column("gitlab_connection_id", sa.String(36), nullable=True),
            sa.Column("gitlab_project_path", sa.String(200), nullable=True),
            sa.Column("pending_actions", sa.JSON, nullable=True),
            sa.Column("started_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("finished_at", sa.DateTime, nullable=True),
            sa.Column("error", sa.Text, nullable=True),
        )
        op.create_index(
            "ix_automation_runs_status_pipeline",
            "automation_runs",
            ["status", "gitlab_pipeline_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_automation_runs_status_pipeline", table_name="automation_runs")
    op.drop_table("automation_runs")
    op.drop_table("automation_rules")
