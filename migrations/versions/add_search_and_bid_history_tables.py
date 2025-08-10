"""add search and bid history tables

Revision ID: add_search_and_bid_history_tables
Revises: e32db374c18c
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_search_and_bid_history_tables'
down_revision = 'add_ended_at_to_auction_results'
branch_labels = None
depends_on = None


def upgrade():
    # Create search_history table
    op.create_table('search_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('query', sa.String(length=255), nullable=False),
        sa.Column('search_type', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create bid_history table
    op.create_table('bid_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('subcategory_id', sa.Integer(), nullable=False),
        sa.Column('seller_id', sa.Integer(), nullable=False),
        sa.Column('bid_count', sa.Integer(), nullable=True),
        sa.Column('last_bid_time', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.ForeignKeyConstraint(['seller_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['subcategory_id'], ['subcategories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('bid_history')
    op.drop_table('search_history')
