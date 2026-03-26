"""EL038: Add sprints and sprint_issues tables.

Revision ID: el038_sprint_tables
Revises: el031_article_versions
Create Date: 2026-03-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "el038_sprint_tables"
down_revision = "el031_article_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sprints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("goal", sa.Text, nullable=True),
        sa.Column("start_date", sa.DateTime, nullable=True),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "sprint_issues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "sprint_id",
            sa.String(36),
            sa.ForeignKey("sprints.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "issue_id",
            sa.String(36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rank", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("sprint_id", "issue_id", name="uq_sprint_issue"),
    )


def downgrade() -> None:
    op.drop_table("sprint_issues")
    op.drop_table("sprints")
