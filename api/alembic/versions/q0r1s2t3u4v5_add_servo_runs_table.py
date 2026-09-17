"""add servo_runs table (servo backfill history)

A backfill re-runs the ingest chain over attributes that are already indexed.
OpenSearch executes it asynchronously and returns a task id, so each run needs
a row to poll against and to answer "what did we rewrite, and when" afterwards.

Revision ID: q0r1s2t3u4v5
Revises: p9q0r1s2t3u4
"""

import sqlalchemy as sa
from alembic import op

revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "servo_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("filter_query", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("opensearch_task_id", sa.String(length=128), nullable=True),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        # The history outlives the operator: a deleted user must not take the
        # record of what they rewrote with them.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_servo_runs_id", "servo_runs", ["id"])
    op.create_index("ix_servo_runs_status", "servo_runs", ["status"])
    op.create_index("ix_servo_runs_created_at", "servo_runs", ["created_at"])


def downgrade():
    op.drop_index("ix_servo_runs_created_at", table_name="servo_runs")
    op.drop_index("ix_servo_runs_status", table_name="servo_runs")
    op.drop_index("ix_servo_runs_id", table_name="servo_runs")
    op.drop_table("servo_runs")
