"""GH ID of an org

Revision ID: 7ec05e286a8d
Revises: a6bcb7491597
Create Date: 2021-10-21 15:30:10.424543

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ec05e286a8d'
down_revision = '559a19cb2cc1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE github_orgs ADD github_id INTEGER NOT NULL DEFAULT (1)')


def downgrade():
    op.drop_column('github_orgs', 'github_id')
