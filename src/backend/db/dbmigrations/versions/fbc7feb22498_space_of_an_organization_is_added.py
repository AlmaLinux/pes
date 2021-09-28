"""Space of an organization is added

Revision ID: fbc7feb22498
Revises: 17b557483dc3
Create Date: 2021-09-28 13:26:00.924992

"""
from alembic import op
import sqlalchemy as sa

from db.data_models import MAIN_ORGANIZATION

# revision identifiers, used by Alembic.

revision = 'fbc7feb22498'
down_revision = '17b557483dc3'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(f"ALTER TABLE actions ADD github_org VARCHAR "
               f"NOT NULL DEFAULT ('{MAIN_ORGANIZATION}')")


def downgrade():
    op.drop_column('actions', 'github_org')
