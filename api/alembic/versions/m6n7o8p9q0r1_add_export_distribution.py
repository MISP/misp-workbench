"""add export distribution

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-06-12 00:00:00.000000

MISP-format exports build a single MISP event; the event distribution level is
captured per export.

"""

import sqlalchemy as sa
from alembic import op

revision = "m6n7o8p9q0r1"
down_revision = "l5m6n7o8p9q0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exports", sa.Column("distribution", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("exports", "distribution")
