"""add hunt run history table

Revision ID: b3e9f1a2c4d7
Revises: 8f3a2d1e9b7c
Create Date: 2026-02-26 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3e9f1a2c4d7"
down_revision = "8f3a2d1e9b7c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hunt_run_history",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("hunt_id", sa.Integer(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["hunt_id"], ["hunts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_hunt_run_history_hunt_id", "hunt_run_history", ["hunt_id"])


def downgrade():
    op.drop_index("ix_hunt_run_history_hunt_id", table_name="hunt_run_history")
    op.drop_table("hunt_run_history")
