"""per-user notebook pins (drop lab_notebooks.is_pinned, add lab_notebook_pins)

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-05-12 00:00:01.000000

Pinning is a per-user bookmark, not a property of the notebook itself —
two viewers of the same global notebook can pin it independently. Moves
the previous boolean on ``lab_notebooks.is_pinned`` to a join table.

"""

from alembic import op
import sqlalchemy as sa


revision = "j3k4l5m6n7o8"
down_revision = "i2j3k4l5m6n7"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("lab_notebooks", "is_pinned")
    op.create_table(
        "lab_notebook_pins",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "notebook_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["notebook_id"], ["lab_notebooks.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_lab_notebook_pins_user_id", "lab_notebook_pins", ["user_id"]
    )


def downgrade():
    op.drop_index("ix_lab_notebook_pins_user_id", table_name="lab_notebook_pins")
    op.drop_table("lab_notebook_pins")
    op.add_column(
        "lab_notebooks",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
