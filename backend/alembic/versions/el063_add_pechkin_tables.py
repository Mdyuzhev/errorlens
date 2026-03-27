"""Add Pechkin (HTTP client) tables

Revision ID: el063_pechkin
Revises: el062
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = "el063_pechkin"
down_revision = "el062"
branch_labels = None
depends_on = None


def upgrade():
    # 1. pechkin_collections
    op.create_table(
        "pechkin_collections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("initial_variables", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # 2. pechkin_folders
    op.create_table(
        "pechkin_folders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("pechkin_collections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("pechkin_folders.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # 3. pechkin_requests
    op.create_table(
        "pechkin_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("pechkin_collections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("folder_id", sa.String(36), sa.ForeignKey("pechkin_folders.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("headers", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("body_type", sa.String(30), nullable=False, server_default="'none'"),
        sa.Column("auth", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("pre_request_script", sa.Text, nullable=True),
        sa.Column("test_script", sa.Text, nullable=True),
        sa.Column("test_snippets", sa.JSON, nullable=True, server_default="[]"),
        sa.Column("extract_variables", sa.JSON, nullable=True, server_default="[]"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    # 4. pechkin_variables
    op.create_table(
        "pechkin_variables",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("collection_id", sa.String(36), sa.ForeignKey("pechkin_collections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("scope", sa.String(50), nullable=False, server_default="'collection'"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("value", sa.Text, nullable=False, server_default="''"),
        sa.Column("is_secret", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # 5. pechkin_request_history
    op.create_table(
        "pechkin_request_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_id", sa.String(36), sa.ForeignKey("pechkin_requests.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("resolved_url", sa.Text, nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("request_headers", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("request_body", sa.Text, nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("response_headers", sa.JSON, nullable=True, server_default="{}"),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade():
    op.drop_table("pechkin_request_history")
    op.drop_table("pechkin_variables")
    op.drop_table("pechkin_requests")
    op.drop_table("pechkin_folders")
    op.drop_table("pechkin_collections")
