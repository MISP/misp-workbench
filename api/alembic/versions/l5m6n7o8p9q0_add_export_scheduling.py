"""add export scheduling

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-06-12 00:00:00.000000

Recurring exports: an export can carry a redbeat schedule so it re-runs
regularly, overwriting its own artifact in place.

"""

import sqlalchemy as sa
from alembic import op

revision = "l5m6n7o8p9q0"
down_revision = "k4l5m6n7o8p9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exports", sa.Column("schedule", sa.JSON(), nullable=True))
    op.add_column(
        "exports", sa.Column("scheduled_task_name", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "exports",
        sa.Column(
            "schedule_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "exports", sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("exports", "last_run_at")
    op.drop_column("exports", "schedule_enabled")
    op.drop_column("exports", "scheduled_task_name")
    op.drop_column("exports", "schedule")
