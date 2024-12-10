"""Added macro table

Revision ID: 4fc1c39216c9
Revises: a5f283a4cfde
Create Date: 2024-12-02 18:56:02.365942

"""
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision = '4fc1c39216c9'
down_revision = 'a5f283a4cfde'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('macro',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', mysql.BIGINT(display_width=18), nullable=False),
    sa.Column('name', mysql.TEXT(), nullable=False, unique=True),
    sa.Column('text', mysql.TEXT(), nullable=False),
    sa.Column('created_at', mysql.TIMESTAMP(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('macro')
    # ### end Alembic commands ###
