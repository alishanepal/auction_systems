"""add status to users table

Revision ID: add_status_to_users_table
Revises: add_search_and_bid_history_tables
Create Date: 2025-08-10 18:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_status_to_users_table'
down_revision = 'add_search_and_bid_history_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column to users table with default value 'pending'
    op.add_column('users', sa.Column('status', sa.String(20), nullable=False, server_default='pending'))


def downgrade():
    # Remove status column from users table
    op.drop_column('users', 'status')
