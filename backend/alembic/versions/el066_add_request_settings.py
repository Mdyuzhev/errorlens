"""Add settings JSON to pechkin_requests

Revision ID: el066
Revises: el065_article_links
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = 'el066'
down_revision = 'el065_article_links'


def upgrade() -> None:
    op.add_column(
        'pechkin_requests',
        sa.Column('settings', sa.JSON(), nullable=True, server_default='{}')
    )


def downgrade() -> None:
    op.drop_column('pechkin_requests', 'settings')
