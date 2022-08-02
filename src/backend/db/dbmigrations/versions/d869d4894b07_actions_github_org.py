"""actions_github_org

Revision ID: d869d4894b07
Revises: 72c9413f4169
Create Date: 2022-07-15 09:07:12.384612

"""
import sqlalchemy as sa
from alembic import op
from db.db_models import Action, GitHubOrg


# revision identifiers, used by Alembic.
from db.utils import session_scope

revision = 'd869d4894b07'
down_revision = '72c9413f4169'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'actions',
        sa.Column('github_org_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'actions_github_orgs',
        'actions',
        'github_orgs',
        ['github_org_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.execute('UPDATE actions SET github_org_id=subquery.id FROM '
               '(SELECT id, name FROM github_orgs) AS subquery '
               'WHERE actions.github_org = subquery.name')
    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint('actions_github_orgs', 'actions', type_='foreignkey')
    op.drop_column('actions', 'github_org_id')
    # ### end Alembic
