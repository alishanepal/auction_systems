"""add_bidder_minimum_amounts_table_only

Revision ID: 2e11418950cb
Revises: 0faf7002e5f7
Create Date: 2025-08-31 21:18:32.659238

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e11418950cb'
down_revision = '0faf7002e5f7'
branch_labels = None
depends_on = None


def upgrade():
    # Create bidder_minimum_amounts table
    op.create_table('bidder_minimum_amounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bidder_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('auction_id', sa.Integer(), nullable=False),
        sa.Column('minimum_amount', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['auction_id'], ['auctions.id'], ),
        sa.ForeignKeyConstraint(['bidder_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bidder_id', 'auction_id', name='uq_bidder_minimum_amount_bidder_auction')
    )


def downgrade():
    # Drop bidder_minimum_amounts table
    op.drop_table('bidder_minimum_amounts')
