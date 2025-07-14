"""add user settings table

Revision ID: 9541c0537355
Revises: 5a6b6047d311
Create Date: 2025-07-14 08:33:23.338041

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9541c0537355'
down_revision = '5a6b6047d311'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False, default={}),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
    )


def downgrade():
    op.drop_table("user_settings")