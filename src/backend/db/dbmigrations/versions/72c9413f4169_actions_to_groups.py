"""actions_to_groups

Revision ID: 72c9413f4169
Revises: 095ba4df0349
Create Date: 2022-07-14 08:34:55.627672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72c9413f4169'
down_revision = '095ba4df0349'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('groups_actions',
    sa.Column('action_id', sa.Integer(), nullable=True),
    sa.Column('group_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['action_id'], ['actions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE')
    )
    # ### end Alembic commands ###


def downgrade():
    op.drop_table('groups_actions')
    # ### end Alembic commands ###
