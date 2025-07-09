"""add settings table

Revision ID: 5a6b6047d311
Revises: 39cbeba07d8b
Create Date: 2025-07-09 11:53:55.375601

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a6b6047d311'
down_revision = '39cbeba07d8b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False, default={}),
    )


def downgrade():
    op.drop_table("settings")
