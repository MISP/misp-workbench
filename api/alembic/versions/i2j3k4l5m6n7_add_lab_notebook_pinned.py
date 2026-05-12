"""add is_pinned to lab_notebooks

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-05-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "i2j3k4l5m6n7"
down_revision = "h1i2j3k4l5m6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "lab_notebooks",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade():
    op.drop_column("lab_notebooks", "is_pinned")
