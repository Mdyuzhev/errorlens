"""Add multi-tenancy fields to all entities

Revision ID: a1b2c3d4e5f6
Revises: cf97fdaebffd
Create Date: 2025-12-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cf97fdaebffd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add multi-tenancy columns."""
    # Add plan column to projects
    op.add_column('projects', sa.Column('plan', sa.String(length=20), nullable=True))
    op.execute("UPDATE projects SET plan = 'free' WHERE plan IS NULL")

    # Add project_id to sessions
    op.add_column('sessions', sa.Column('project_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_sessions_project_id', 'sessions', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE'
    )

    # Add project_id to test_cases
    op.add_column('test_cases', sa.Column('project_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_test_cases_project_id', 'test_cases', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE'
    )

    # Add project_id to tasks
    op.add_column('tasks', sa.Column('project_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_tasks_project_id', 'tasks', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE'
    )

    # Add project_id and created_by to articles
    op.add_column('articles', sa.Column('project_id', sa.String(length=36), nullable=True))
    op.add_column('articles', sa.Column('created_by', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_articles_project_id', 'articles', 'projects',
        ['project_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_articles_created_by', 'articles', 'users',
        ['created_by'], ['id'], ondelete='SET NULL'
    )

    # Add added_by_id to project_members and rename joined_at to added_at
    op.add_column('project_members', sa.Column('added_by_id', sa.String(length=36), nullable=True))
    op.create_foreign_key(
        'fk_project_members_added_by', 'project_members', 'users',
        ['added_by_id'], ['id'], ondelete='SET NULL'
    )
    # Rename joined_at to added_at
    op.alter_column('project_members', 'joined_at', new_column_name='added_at')


def downgrade() -> None:
    """Remove multi-tenancy columns."""
    # Revert project_members changes
    op.alter_column('project_members', 'added_at', new_column_name='joined_at')
    op.drop_constraint('fk_project_members_added_by', 'project_members', type_='foreignkey')
    op.drop_column('project_members', 'added_by_id')

    # Revert articles changes
    op.drop_constraint('fk_articles_created_by', 'articles', type_='foreignkey')
    op.drop_constraint('fk_articles_project_id', 'articles', type_='foreignkey')
    op.drop_column('articles', 'created_by')
    op.drop_column('articles', 'project_id')

    # Revert tasks changes
    op.drop_constraint('fk_tasks_project_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'project_id')

    # Revert test_cases changes
    op.drop_constraint('fk_test_cases_project_id', 'test_cases', type_='foreignkey')
    op.drop_column('test_cases', 'project_id')

    # Revert sessions changes
    op.drop_constraint('fk_sessions_project_id', 'sessions', type_='foreignkey')
    op.drop_column('sessions', 'project_id')

    # Revert projects changes
    op.drop_column('projects', 'plan')
