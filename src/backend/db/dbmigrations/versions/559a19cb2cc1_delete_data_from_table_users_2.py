"""Delete data from table `users` & `github_orgs` because they aren't
invalid and not necessary

Revision ID: 559a19cb2cc1
Revises: a6bcb7491597
Create Date: 2021-09-24 15:47:39.742310

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '559a19cb2cc1'
down_revision = 'a6bcb7491597'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('DELETE FROM github_orgs')
    op.execute('DELETE FROM users')


def downgrade():
    pass
