"""Add version field for Action

Revision ID: 99fb2af8e09a
Revises: 
Create Date: 2021-09-24 12:07:38.320369

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99fb2af8e09a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE actions ADD version INTEGER NOT NULL DEFAULT (1)')


def downgrade():
    op.drop_column('actions', 'version')
