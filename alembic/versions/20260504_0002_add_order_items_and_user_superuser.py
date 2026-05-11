"""add order_items table if missing and ensure users.is_superuser exists

Revision ID: 20260504_0002
Revises: 20260504_0001
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "20260504_0002"
down_revision = "20260504_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # Ensure order_items table exists
    if "order_items" not in tables:
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
        )

    # Ensure users.is_superuser column exists
    if "users" in tables:
        columns = {c["name"] for c in inspector.get_columns("users")}
        if "is_superuser" not in columns:
            op.add_column("users", sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False))

    # Ensure products.image_url column exists (may already be there from migration 0001)
    if "products" in tables:
        columns = {c["name"] for c in inspector.get_columns("products")}
        if "image_url" not in columns:
            op.add_column("products", sa.Column("image_url", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "order_items" in tables:
        op.drop_table("order_items")
