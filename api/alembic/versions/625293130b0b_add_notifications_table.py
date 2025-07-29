"""add notifications table

Revision ID: 625293130b0b
Revises: 054d8a965f31
Create Date: 2025-07-29 14:25:15.673652

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "625293130b0b"
down_revision = "054d8a965f31"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(255)),
        sa.Column("entity_uuid", sa.types.Uuid(as_uuid=False), nullable=False),
        sa.Column("read", sa.Boolean, default=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, default={}),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
    )


def downgrade():
    op.drop_table("notifications")
