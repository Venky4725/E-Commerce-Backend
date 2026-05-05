"""add cart_items table and unique constraint on carts.user_id

Revision ID: 20260504_0001
Revises: 20260427_0001_add_product_image_url
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260504_0001"
down_revision = "20260427_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove duplicate carts per user (keep the oldest one)
    op.execute("""
        DELETE FROM carts
        WHERE id NOT IN (
            SELECT MIN(id) FROM carts GROUP BY user_id
        )
    """)

    # 2. Add unique constraint on carts.user_id
    op.create_unique_constraint("uq_cart_user_id", "carts", ["user_id"])

    # 3. Create cart_items table
    op.create_table(
        "cart_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("cart_id", sa.Integer(), sa.ForeignKey("carts.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_item_product"),
    )


def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_constraint("uq_cart_user_id", "carts", type_="unique")
