"""add launch metadata fields to test_runs

Revision ID: el062
Revises: el046_linked_articles
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'el062'
down_revision = 'el046_linked_articles'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('test_runs', sa.Column('launch_name', sa.String(200), nullable=True))
    op.add_column('test_runs', sa.Column('branch', sa.String(100), nullable=True))
    op.add_column('test_runs', sa.Column('environment', sa.String(100), nullable=True))
    op.add_column('test_runs', sa.Column('pipeline_id', sa.String(100), nullable=True))
    op.add_column('test_runs', sa.Column('source', sa.String(20), nullable=False, server_default='allure'))

def downgrade() -> None:
    op.drop_column('test_runs', 'source')
    op.drop_column('test_runs', 'pipeline_id')
    op.drop_column('test_runs', 'environment')
    op.drop_column('test_runs', 'branch')
    op.drop_column('test_runs', 'launch_name')
