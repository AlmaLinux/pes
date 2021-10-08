"""History timestamp

Revision ID: dc2ce12e8607
Revises: fbc7feb22498
Create Date: 2021-10-07 15:57:02.724453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dc2ce12e8607'
down_revision = 'fbc7feb22498'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('actions_history',
                  sa.Column('timestamp', sa.DateTime(), nullable=True))
    op.execute('update actions_history set timestamp = current_timestamp')


def downgrade():
    op.drop_column('actions_history', 'timestamp')
