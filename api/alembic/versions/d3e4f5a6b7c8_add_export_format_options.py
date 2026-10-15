"""add export format options

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-15 09:00:00.000000

Options of the detection-engine export formats (Suricata rules, Zeek Intel,
DNS RPZ): the rules' action and the zone's policy.

"""

import sqlalchemy as sa
from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exports", sa.Column("format_options", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("exports", "format_options")
