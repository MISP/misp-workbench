"""add incremental export feeds

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-10-07 00:00:00.000000

Exports can be materialized as incremental feeds: each run writes the full
artifact plus a delta since the previous run, tracked in ``export_deltas``.
``checksum`` lets the stored artifact be served with a stable ETag.

"""

import sqlalchemy as sa
from alembic import op

revision = "t3u4v5w6x7y8"
down_revision = "s2t3u4v5w6x7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exports", sa.Column("checksum", sa.String(length=64), nullable=True))
    op.add_column(
        "exports",
        sa.Column(
            "incremental", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("exports", sa.Column("cursor", sa.BigInteger(), nullable=True))
    op.create_table(
        "export_deltas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "export_id",
            sa.Integer(),
            sa.ForeignKey("exports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("since", sa.BigInteger(), nullable=False),
        sa.Column("until", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("export_id", "seq"),
    )
    op.create_index("ix_export_deltas_id", "export_deltas", ["id"])
    op.create_index("ix_export_deltas_export_id", "export_deltas", ["export_id"])


def downgrade():
    op.drop_index("ix_export_deltas_export_id", table_name="export_deltas")
    op.drop_index("ix_export_deltas_id", table_name="export_deltas")
    op.drop_table("export_deltas")
    op.drop_column("exports", "cursor")
    op.drop_column("exports", "incremental")
    op.drop_column("exports", "checksum")
