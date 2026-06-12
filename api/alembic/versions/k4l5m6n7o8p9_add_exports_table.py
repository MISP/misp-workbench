"""add exports table

Revision ID: k4l5m6n7o8p9
Revises: j3k4l5m6n7o8
Create Date: 2026-06-09 00:00:00.000000

Async IOC export jobs: an OpenSearch query is run in a Celery task, the
results are transformed (json/csv/stix) and stored in local/Garage storage.
The row tracks job state and points at the produced artifact.

"""

from alembic import op
import sqlalchemy as sa

revision = "k4l5m6n7o8p9"
down_revision = "j3k4l5m6n7o8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "exports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("index_target", sa.String(length=50), nullable=False),
        sa.Column("format", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("record_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_exports_id", "exports", ["id"])
    op.create_index("ix_exports_user_id", "exports", ["user_id"])


def downgrade():
    op.drop_index("ix_exports_user_id", table_name="exports")
    op.drop_index("ix_exports_id", table_name="exports")
    op.drop_table("exports")
