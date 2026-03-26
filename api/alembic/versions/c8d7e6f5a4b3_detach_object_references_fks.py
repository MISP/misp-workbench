"""detach object_references FK constraints to events and objects

These are the last DB-level FK constraints that reference the events and objects
tables from an external table, blocking their eventual removal.

Revision ID: c8d7e6f5a4b3
Revises: f3e2d1c0b9a8
Create Date: 2026-03-25 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d7e6f5a4b3"
down_revision = "f3e2d1c0b9a8"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "object_references_event_id_fkey", "object_references", type_="foreignkey"
    )
    op.drop_constraint(
        "object_references_object_id_fkey", "object_references", type_="foreignkey"
    )


def downgrade():
    op.create_foreign_key(
        "object_references_event_id_fkey",
        "object_references",
        "events",
        ["event_id"],
        ["id"],
    )
    op.create_foreign_key(
        "object_references_object_id_fkey",
        "object_references",
        "objects",
        ["object_id"],
        ["id"],
    )
