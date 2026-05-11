"""add product snapshot to order items

Revision ID: 20260511_0001
Revises: 20260504_0003
Create Date: 2026-05-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260511_0001'
down_revision = '20260504_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add product_name column to order_items
    op.add_column('order_items', sa.Column('product_name', sa.String(), nullable=True))
    
    # Add product_image_url column to order_items
    op.add_column('order_items', sa.Column('product_image_url', sa.String(), nullable=True))
    
    # Add is_active column to products (for soft delete)
    op.add_column('products', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('products', 'is_active')
    op.drop_column('order_items', 'product_image_url')
    op.drop_column('order_items', 'product_name')
