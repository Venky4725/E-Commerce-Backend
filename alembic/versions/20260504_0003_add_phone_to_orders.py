"""add phone column to orders table

Revision ID: 20260504_0003
Revises: 20260504_0002
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "20260504_0003"
down_revision = "20260504_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if "orders" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("orders")}
        if "phone" not in columns:
            op.add_column("orders", sa.Column("phone", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    if "orders" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("orders")}
        if "phone" in columns:
            op.drop_column("orders", "phone")
