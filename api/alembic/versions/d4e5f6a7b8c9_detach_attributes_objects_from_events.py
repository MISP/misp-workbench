"""remove event_id columns from attributes and objects tables

Revision ID: d4e5f6a7b8c9
Revises: c8d7e6f5a4b3
Create Date: 2026-03-25 00:00:00.000000

"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c8d7e6f5a4b3"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_attributes_event_id", table_name="attributes", if_exists=True)
    op.drop_column("attributes", "event_id")
    op.drop_index("ix_objects_event_id", table_name="objects", if_exists=True)
    op.drop_column("objects", "event_id")


def downgrade():
    import sqlalchemy as sa

    op.add_column("objects", sa.Column("event_id", sa.Integer(), nullable=True))
    op.create_index("ix_objects_event_id", "objects", ["event_id"])
    op.add_column("attributes", sa.Column("event_id", sa.Integer(), nullable=True))
    op.create_index("ix_attributes_event_id", "attributes", ["event_id"])
