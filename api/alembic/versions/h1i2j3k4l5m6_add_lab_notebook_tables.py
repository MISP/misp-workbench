"""add lab notebook tables (tech lab)

Revision ID: h1i2j3k4l5m6
Revises: g7h8i9j0k1l2
Create Date: 2026-05-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "h1i2j3k4l5m6"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lab_folders",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["lab_folders.id"],
            ondelete="CASCADE",
            use_alter=True,
        ),
    )
    op.create_index("ix_lab_folders_user_id", "lab_folders", ["user_id"])
    op.create_index("ix_lab_folders_parent_id", "lab_folders", ["parent_id"])
    op.create_index("ix_lab_folders_visibility", "lab_folders", ["visibility"])

    op.create_table(
        "lab_notebooks",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=True),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default=""),
        sa.Column("cell_outputs", JSONB, nullable=False, server_default="{}"),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["folder_id"], ["lab_folders.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_lab_notebooks_user_id", "lab_notebooks", ["user_id"])
    op.create_index("ix_lab_notebooks_folder_id", "lab_notebooks", ["folder_id"])
    op.create_index("ix_lab_notebooks_visibility", "lab_notebooks", ["visibility"])

    op.create_table(
        "lab_executions",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cell_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("outputs", JSONB, nullable=False, server_default="[]"),
        sa.Column("execution_count", sa.Integer(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["notebook_id"], ["lab_notebooks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_lab_executions_notebook_id_started_at",
        "lab_executions",
        ["notebook_id", sa.text("started_at DESC")],
    )
    op.create_index("ix_lab_executions_status", "lab_executions", ["status"])


def downgrade():
    op.drop_index("ix_lab_executions_status", table_name="lab_executions")
    op.drop_index(
        "ix_lab_executions_notebook_id_started_at", table_name="lab_executions"
    )
    op.drop_table("lab_executions")
    op.drop_index("ix_lab_notebooks_visibility", table_name="lab_notebooks")
    op.drop_index("ix_lab_notebooks_folder_id", table_name="lab_notebooks")
    op.drop_index("ix_lab_notebooks_user_id", table_name="lab_notebooks")
    op.drop_table("lab_notebooks")
    op.drop_index("ix_lab_folders_visibility", table_name="lab_folders")
    op.drop_index("ix_lab_folders_parent_id", table_name="lab_folders")
    op.drop_index("ix_lab_folders_user_id", table_name="lab_folders")
    op.drop_table("lab_folders")
