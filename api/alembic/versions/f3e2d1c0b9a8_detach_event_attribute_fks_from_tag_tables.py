"""detach event/attribute FK constraints from event_tags and attribute_tags

These FK constraints block dropping the events and attributes tables.
The tag junction tables will remain, referencing only the tags table.

Revision ID: f3e2d1c0b9a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-25 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f3e2d1c0b9a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "event_tags_event_id_fkey", "event_tags", type_="foreignkey"
    )
    op.drop_constraint(
        "attribute_tags_attribute_id_fkey", "attribute_tags", type_="foreignkey"
    )
    op.drop_constraint(
        "attribute_tags_event_id_fkey", "attribute_tags", type_="foreignkey"
    )
    # Allow NULLs now that FK constraints are removed (events/attributes may not exist in SQL)
    op.alter_column("event_tags", "event_id", nullable=True)
    op.alter_column("attribute_tags", "event_id", nullable=True)
    op.alter_column("attribute_tags", "attribute_id", nullable=True)


def downgrade():
    op.alter_column("attribute_tags", "attribute_id", nullable=False)
    op.alter_column("attribute_tags", "event_id", nullable=False)
    op.alter_column("event_tags", "event_id", nullable=False)
    op.create_foreign_key(
        "event_tags_event_id_fkey",
        "event_tags",
        "events",
        ["event_id"],
        ["id"],
    )
    op.create_foreign_key(
        "attribute_tags_attribute_id_fkey",
        "attribute_tags",
        "attributes",
        ["attribute_id"],
        ["id"],
    )
    op.create_foreign_key(
        "attribute_tags_event_id_fkey",
        "attribute_tags",
        "events",
        ["event_id"],
        ["id"],
    )
