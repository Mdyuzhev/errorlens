"""Add multi-tenancy fields to all entities

Revision ID: a1b2c3d4e5f6
Revises: cf97fdaebffd
Create Date: 2025-12-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cf97fdaebffd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists in table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add multi-tenancy columns.

    Uses batch mode for SQLite compatibility.
    Checks column existence to make migration idempotent.
    """
    # Add plan column to projects (if not exists)
    if not column_exists('projects', 'plan'):
        with op.batch_alter_table('projects', schema=None) as batch_op:
            batch_op.add_column(sa.Column('plan', sa.String(length=20), nullable=True, server_default='free'))

    # Add project_id to sessions (if not exists)
    if not column_exists('sessions', 'project_id'):
        with op.batch_alter_table('sessions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('project_id', sa.String(length=36), nullable=True))

    # Add project_id to test_cases (if not exists)
    if not column_exists('test_cases', 'project_id'):
        with op.batch_alter_table('test_cases', schema=None) as batch_op:
            batch_op.add_column(sa.Column('project_id', sa.String(length=36), nullable=True))

    # Add project_id to tasks (if not exists)
    if not column_exists('tasks', 'project_id'):
        with op.batch_alter_table('tasks', schema=None) as batch_op:
            batch_op.add_column(sa.Column('project_id', sa.String(length=36), nullable=True))

    # Add project_id and created_by to articles (if not exists)
    if not column_exists('articles', 'project_id'):
        with op.batch_alter_table('articles', schema=None) as batch_op:
            batch_op.add_column(sa.Column('project_id', sa.String(length=36), nullable=True))

    if not column_exists('articles', 'created_by'):
        with op.batch_alter_table('articles', schema=None) as batch_op:
            batch_op.add_column(sa.Column('created_by', sa.String(length=36), nullable=True))

    # Handle project_members: add added_by_id and rename joined_at to added_at
    if not column_exists('project_members', 'added_by_id'):
        with op.batch_alter_table('project_members', schema=None) as batch_op:
            batch_op.add_column(sa.Column('added_by_id', sa.String(length=36), nullable=True))

    # Rename joined_at to added_at if needed
    if column_exists('project_members', 'joined_at') and not column_exists('project_members', 'added_at'):
        with op.batch_alter_table('project_members', schema=None) as batch_op:
            batch_op.add_column(sa.Column('added_at', sa.DateTime(), nullable=True))
        op.execute("UPDATE project_members SET added_at = joined_at WHERE added_at IS NULL")
        with op.batch_alter_table('project_members', schema=None) as batch_op:
            batch_op.drop_column('joined_at')


def downgrade() -> None:
    """Remove multi-tenancy columns."""
    # Revert project_members changes
    if column_exists('project_members', 'added_at') and not column_exists('project_members', 'joined_at'):
        with op.batch_alter_table('project_members', schema=None) as batch_op:
            batch_op.add_column(sa.Column('joined_at', sa.DateTime(), nullable=True))
        op.execute("UPDATE project_members SET joined_at = added_at WHERE joined_at IS NULL")
        with op.batch_alter_table('project_members', schema=None) as batch_op:
            batch_op.drop_column('added_at')

    if column_exists('project_members', 'added_by_id'):
        with op.batch_alter_table('project_members', schema=None) as batch_op:
            batch_op.drop_column('added_by_id')

    # Revert articles changes
    if column_exists('articles', 'created_by'):
        with op.batch_alter_table('articles', schema=None) as batch_op:
            batch_op.drop_column('created_by')

    if column_exists('articles', 'project_id'):
        with op.batch_alter_table('articles', schema=None) as batch_op:
            batch_op.drop_column('project_id')

    # Revert tasks changes
    if column_exists('tasks', 'project_id'):
        with op.batch_alter_table('tasks', schema=None) as batch_op:
            batch_op.drop_column('project_id')

    # Revert test_cases changes
    if column_exists('test_cases', 'project_id'):
        with op.batch_alter_table('test_cases', schema=None) as batch_op:
            batch_op.drop_column('project_id')

    # Revert sessions changes
    if column_exists('sessions', 'project_id'):
        with op.batch_alter_table('sessions', schema=None) as batch_op:
            batch_op.drop_column('project_id')

    # Revert projects changes
    if column_exists('projects', 'plan'):
        with op.batch_alter_table('projects', schema=None) as batch_op:
            batch_op.drop_column('plan')
