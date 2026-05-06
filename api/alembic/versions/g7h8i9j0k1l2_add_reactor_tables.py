"""add reactor tables (tech lab)

Revision ID: g7h8i9j0k1l2
Revises: 5b6c7d8e9f01
Create Date: 2026-04-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "g7h8i9j0k1l2"
down_revision = "5b6c7d8e9f01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reactor_scripts",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=32), nullable=False, server_default="python"),
        sa.Column("source_uri", sa.String(length=512), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("entrypoint", sa.String(length=255), nullable=False, server_default="handle"),
        sa.Column("triggers", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_writes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(length=32), nullable=True),
        sa.Column("last_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_reactor_scripts_user_id", "reactor_scripts", ["user_id"]
    )
    op.create_index(
        "ix_reactor_scripts_status", "reactor_scripts", ["status"]
    )

    op.create_table(
        "reactor_runs",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("script_id", sa.Integer(), nullable=False),
        sa.Column("triggered_by", JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("log_uri", sa.String(length=512), nullable=True),
        sa.Column("writes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["script_id"], ["reactor_scripts.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_reactor_runs_script_id_started_at",
        "reactor_runs",
        ["script_id", sa.text("started_at DESC")],
    )
    op.create_index("ix_reactor_runs_status", "reactor_runs", ["status"])

    op.create_foreign_key(
        "fk_reactor_scripts_last_run_id",
        "reactor_scripts",
        "reactor_runs",
        ["last_run_id"],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )


def downgrade():
    op.drop_constraint(
        "fk_reactor_scripts_last_run_id", "reactor_scripts", type_="foreignkey"
    )
    op.drop_index("ix_reactor_runs_status", table_name="reactor_runs")
    op.drop_index(
        "ix_reactor_runs_script_id_started_at", table_name="reactor_runs"
    )
    op.drop_table("reactor_runs")
    op.drop_index("ix_reactor_scripts_status", table_name="reactor_scripts")
    op.drop_index("ix_reactor_scripts_user_id", table_name="reactor_scripts")
    op.drop_table("reactor_scripts")
