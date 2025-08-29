"""add password hash to user

Revision ID: 2c7a5605bbd9
Revises: 5e9f70669265
Create Date: 2024-05-09 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '2c7a5605bbd9'
down_revision = '5e9f70669265'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('password_hash', sa.String(length=128), nullable=False))


def downgrade():
    op.drop_column('users', 'password_hash')
