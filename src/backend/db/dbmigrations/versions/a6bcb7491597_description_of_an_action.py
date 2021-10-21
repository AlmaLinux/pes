"""Description of an action

Revision ID: a6bcb7491597
Revises: 2396de2c85f2
Create Date: 2021-10-21 12:18:01.158233

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6bcb7491597'
down_revision = '2396de2c85f2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('actions',
                  sa.Column('description', sa.String(), nullable=True))


def downgrade():
    op.drop_column('actions', 'description')
