"""add sinks table

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-10-07 00:00:00.000000

Outbound sinks (Splunk HEC, GELF, syslog/CEF, webhook) that published events'
indicators are pushed to, with their delivery status.

"""

import sqlalchemy as sa

from alembic import op

revision = "u4v5w6x7y8z9"
down_revision = "t3u4v5w6x7y8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sinks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "delivered_count", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sinks_id", "sinks", ["id"])


def downgrade():
    op.drop_index("ix_sinks_id", table_name="sinks")
    op.drop_table("sinks")
