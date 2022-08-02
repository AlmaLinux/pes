"""Sequences in PSQL

Revision ID: f22c7f7e3588
Revises: 7ec05e286a8d
Create Date: 2021-10-28 11:55:28.387334

"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f22c7f7e3588'
down_revision = '7ec05e286a8d'
branch_labels = None
depends_on = None


tables_dict = {
    'actions': 'id',
    'actions_history': 'id',
    'github_orgs': 'id',
    'groups_actions': 'id',
    'modules_streams': 'id',
    'packages': 'id',
    'releases': 'id',
    'users': 'id',
}


def upgrade():
    def execute(command):
        print(f'Command: {command}')
        op.execute(command)

    for table_name, primary_key in tables_dict.items():
        sequence_name = f'{table_name}_{primary_key}_seq'
        execute(f'CREATE SEQUENCE {sequence_name}')
        execute(f"SELECT setval('{sequence_name}', "
                f"(SELECT max({primary_key})+1 from {table_name}), true)")
        execute(f"ALTER TABLE {table_name} ALTER COLUMN {primary_key} "
                f"SET DEFAULT nextval('{sequence_name}')")


def downgrade():
    pass
