"""add user phone and address fields

Revision ID: 20260511_0004
Revises: 20260511_0003
Create Date: 2026-05-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260511_0004'
down_revision = '20260511_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phone and address columns to users table
    op.add_column('users', sa.Column('phone', sa.String(), nullable=True))
    op.add_column('users', sa.Column('address', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove phone and address columns from users table
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone')
