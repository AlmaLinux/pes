"""Delete data from table `users` because it's invalid and not necessary

Revision ID: 559a19cb2cc0
Revises: 99fb2af8e09a
Create Date: 2021-09-24 15:47:39.742310

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '559a19cb2cc0'
down_revision = '99fb2af8e09a'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('DELETE FROM users')


def downgrade():
    pass
