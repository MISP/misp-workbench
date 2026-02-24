"""add hunts table

Revision ID: 8f3a2d1e9b7c
Revises: 625293130b0b
Create Date: 2026-02-24 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f3a2d1e9b7c"
down_revision = "625293130b0b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hunts",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("index_target", sa.String(50), nullable=False, server_default="attributes"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_match_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=True,
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )


def downgrade():
    op.drop_table("hunts")
