"""create module settings table

Revision ID: 149c630ce11f
Revises: e7215f4129ec
Create Date: 2024-07-31 08:51:42.187626

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "149c630ce11f"
down_revision = "e7215f4129ec"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "module_settings",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("module_name", sa.String(255), nullable=False, unique=True),
        sa.Column("created", sa.DateTime()),
        sa.Column("modified", sa.DateTime()),
        sa.Column("config", sa.JSON(), nullable=False, default={}),
    )


def downgrade():
    op.drop_table("module_settings")
