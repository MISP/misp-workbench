"""add source trust

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-10-12 00:00:00.000000

Per-source adjustments to indicator confidence scores: a modifier (points
added to or taken off the score) and an optional cap, on feeds, MISP
servers and organisations.

"""

import sqlalchemy as sa
from alembic import op

revision = "w6x7y8z9a0b1"
down_revision = "v5w6x7y8z9a0"
branch_labels = None
depends_on = None

_TABLES = ("feeds", "servers", "organisations")


def upgrade():
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column(
                "score_modifier", sa.Integer(), nullable=False, server_default="0"
            ),
        )
        op.add_column(table, sa.Column("score_cap", sa.Integer(), nullable=True))


def downgrade():
    for table in _TABLES:
        op.drop_column(table, "score_cap")
        op.drop_column(table, "score_modifier")
