"""add processing status to order enum

Revision ID: 20260511_0003
Revises: 20260511_0002
Create Date: 2026-05-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260511_0003'
down_revision = '20260511_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add PROCESSING to the orderstatus enum
    # PostgreSQL requires special handling for enum types
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'PROCESSING'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values
    # This is a one-way migration
    pass
