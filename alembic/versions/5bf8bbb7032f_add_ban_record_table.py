"""Add ban_record table

Revision ID: 5bf8bbb7032f
Revises: 714c54b442ec
Create Date: 2022-09-01 17:00:37.028176

"""
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision = "5bf8bbb7032f"
down_revision = "714c54b442ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "ban_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", mysql.VARCHAR(length=42), nullable=True),
        sa.Column("reason", mysql.TEXT(), nullable=False),
        sa.Column("moderator", mysql.VARCHAR(length=42), nullable=True),
        sa.Column("unban_time", sa.Integer(), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False),
        sa.Column("unbanned", sa.Boolean(), nullable=False),
        sa.Column("timestamp", mysql.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("ban_record")
    # ### end Alembic commands ###