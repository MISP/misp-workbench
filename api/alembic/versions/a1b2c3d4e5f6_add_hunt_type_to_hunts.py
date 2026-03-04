"""add hunt_type to hunts

Revision ID: a1b2c3d4e5f6
Revises: b3e9f1a2c4d7
Create Date: 2026-03-04 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "b3e9f1a2c4d7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "hunts",
        sa.Column(
            "hunt_type",
            sa.String(50),
            nullable=False,
            server_default="opensearch",
        ),
    )
    op.alter_column("hunts", "index_target", nullable=True)


def downgrade():
    op.alter_column("hunts", "index_target", nullable=False)
    op.drop_column("hunts", "hunt_type")
