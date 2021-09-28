"""
Move field `github_orgs` from table `users` to the separate table

Revision ID: 3065019a055e
Revises: 559a19cb2cc0
Create Date: 2021-09-27 13:14:47.974932

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3065019a055e'
down_revision = '559a19cb2cc0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'github_orgs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'users_github_orgs',
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('github_org_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ('github_org_id',),
            ['github_orgs.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ('user_id',),
            ['users.id'],
            ondelete='CASCADE',
        )
    )
    op.drop_table('users')
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_access_token', sa.String(), nullable=True),
        sa.Column('github_id', sa.Integer(), nullable=False),
        sa.Column('github_login', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.add_column(
        'users',
        sa.Column(
            'github_orgs',
            sa.VARCHAR(),
            nullable=True,
        )
    )
    op.drop_table('users_orgs')
    op.drop_table('github_orgs')
    op.execute('DELETE FROM users')
