"""add servos table (tech lab transformation servos)

Postgres owns the servo definition; the compiled OpenSearch ingest pipeline is
derived from it and re-synced on every mutation and at API startup. The chain
pipeline the servos hang off is repo-managed
(``opensearch/pipelines/misp-attributes_servos.json``) and reset to empty on
every stack start, so the DB is what makes a servo survive a restart.

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "p9q0r1s2t3u4"
down_revision = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "servos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("processors", JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "target_index",
            sa.String(length=255),
            nullable=False,
            server_default="misp-attributes",
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_servos_id", "servos", ["id"])
    op.create_index("ix_servos_slug", "servos", ["slug"], unique=True)
    op.create_index("ix_servos_enabled_position", "servos", ["enabled", "position"])


def downgrade():
    op.drop_index("ix_servos_enabled_position", table_name="servos")
    op.drop_index("ix_servos_slug", table_name="servos")
    op.drop_index("ix_servos_id", table_name="servos")
    op.drop_table("servos")
