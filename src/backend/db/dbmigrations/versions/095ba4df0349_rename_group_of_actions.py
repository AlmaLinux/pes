"""rename group_of_actions

Revision ID: 095ba4df0349
Revises: f22c7f7e3588
Create Date: 2022-02-08 11:51:34.744205

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '095ba4df0349'
down_revision = 'f22c7f7e3588'
branch_labels = None
depends_on = None


def upgrade():
# ### commands auto generated by Alembic - please adjust! ###
    op.create_table('groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('github_org_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['github_org_id'], ['github_orgs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('groups_actions')
    op.alter_column('actions', 'version',
               existing_type=sa.BIGINT(),
               nullable=False,
               existing_server_default=sa.text("'1'::bigint"))
    op.alter_column('actions', 'is_approved',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    op.alter_column('actions', 'action',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('actions', 'arches',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('actions_history', 'history_type',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('actions_history', 'username',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('actions_history', 'action_id',
               existing_type=sa.BIGINT(),
               nullable=False)
    op.alter_column('actions_history', 'timestamp',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False)
    op.alter_column('github_orgs', 'github_id',
               existing_type=sa.BIGINT(),
               nullable=False,
               existing_server_default=sa.text("'1'::bigint"))
    op.alter_column('github_orgs', 'name',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('modules_streams', 'name',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('modules_streams', 'stream',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('packages', 'name',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('packages', 'repository',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('packages', 'type',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('releases', 'os_name',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('releases', 'major_version',
               existing_type=sa.BIGINT(),
               nullable=False)
    op.alter_column('releases', 'minor_version',
               existing_type=sa.BIGINT(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
# ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('releases', 'minor_version',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.alter_column('releases', 'major_version',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.alter_column('releases', 'os_name',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('packages', 'type',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('packages', 'repository',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('packages', 'name',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('modules_streams', 'stream',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('modules_streams', 'name',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('github_orgs', 'name',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('github_orgs', 'github_id',
               existing_type=sa.BIGINT(),
               nullable=True,
               existing_server_default=sa.text("'1'::bigint"))
    op.alter_column('actions_history', 'timestamp',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('actions_history', 'action_id',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.alter_column('actions_history', 'username',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('actions_history', 'history_type',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('actions', 'arches',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('actions', 'action',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('actions', 'is_approved',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.alter_column('actions', 'version',
               existing_type=sa.BIGINT(),
               nullable=True,
               existing_server_default=sa.text("'1'::bigint"))
    op.create_table('groups_actions',
    sa.Column('id', sa.BIGINT(), server_default=sa.text("nextval('groups_actions_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('github_org_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['github_org_id'], ['github_orgs.id'], name='groups_actions_github_org_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='idx_41160_groups_actions_pkey')
    )
    op.drop_table('groups')
    # ### end Alembic commands ###