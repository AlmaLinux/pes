"""Group of actions

Revision ID: 2396de2c85f2
Revises: dc2ce12e8607
Create Date: 2021-10-18 13:18:02.096104

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2396de2c85f2'
down_revision = 'dc2ce12e8607'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'groups_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('github_org_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ('github_org_id',), ['github_orgs.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('groups_actions')
