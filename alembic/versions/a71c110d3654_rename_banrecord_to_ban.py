"""Rename BanRecord to Ban

Revision ID: a71c110d3654
Revises: 32e8037d780c
Create Date: 2023-03-29 00:55:33.080168

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a71c110d3654"
down_revision = "32e8037d780c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.rename_table("ban_record", "ban")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.rename_table("ban", "ban_record")
    # ### end Alembic commands ###