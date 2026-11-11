"""add warninglist sync schedule

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-11-11 09:00:00.000000

How often an organisation's warninglist is synced from its source URL (in
minutes, 0 for manual syncs only; existing lists keep their daily sync), and
how many syncs in a row failed, to back off from a failing source.

"""

import sqlalchemy as sa
from alembic import op

revision = "e4f5a6b7c8d9"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "warninglists",
        sa.Column(
            "sync_every_minutes", sa.Integer(), nullable=False, server_default="1440"
        ),
    )
    op.add_column(
        "warninglists",
        sa.Column("sync_failures", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("warninglists", "sync_failures")
    op.drop_column("warninglists", "sync_every_minutes")
