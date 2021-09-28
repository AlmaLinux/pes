"""History of actions is added

Revision ID: 17b557483dc3
Revises: 3065019a055e
Create Date: 2021-09-27 22:08:45.020523

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17b557483dc3'
down_revision = '3065019a055e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'actions_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action_before', sa.String(), nullable=True),
        sa.Column('action_after', sa.String(), nullable=True),
        sa.Column('history_type', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('action_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('actions_history')
