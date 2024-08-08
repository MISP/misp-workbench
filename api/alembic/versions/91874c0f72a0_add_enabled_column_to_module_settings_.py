"""add enabled column to module settings table

Revision ID: 91874c0f72a0
Revises: 149c630ce11f
Create Date: 2024-07-31 10:00:56.899967

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "91874c0f72a0"
down_revision = "149c630ce11f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "module_settings",
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
    )


def downgrade():
    op.drop_column("module_settings", "enabled")
