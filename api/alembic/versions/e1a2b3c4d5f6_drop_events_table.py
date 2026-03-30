"""drop events table and migrate feeds.event_id to uuid string

Revision ID: e1a2b3c4d5f6
Revises: d4e5f6a7b8c9
Create Date: 2026-03-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e1a2b3c4d5f6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    # Replace event_id (INTEGER) with event_uuid (VARCHAR) in object_references
    op.drop_column("object_references", "event_id")
    op.add_column("object_references", sa.Column("event_uuid", postgresql.UUID(as_uuid=True), nullable=True))

    # Replace event_id (INTEGER) with event_uuid (VARCHAR) in event_tags and attribute_tags
    op.drop_column("event_tags", "event_id")
    op.add_column("event_tags", sa.Column("event_uuid", postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_column("attribute_tags", "event_id")
    op.add_column("attribute_tags", sa.Column("event_uuid", postgresql.UUID(as_uuid=True), nullable=True))

    # Rename feeds.event_id (INTEGER) to feeds.event_uuid (VARCHAR for UUID string)
    op.drop_column("feeds", "event_id")
    op.add_column("feeds", sa.Column("event_uuid", postgresql.UUID(as_uuid=True), nullable=True))

    # Drop the events table (all FK constraints were removed in prior migrations)
    op.drop_table("events")


def downgrade():
    # Recreate events table (minimal schema for rollback)
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("info", sa.String(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attribute_count", sa.Integer(), nullable=True),
        sa.Column("object_count", sa.Integer(), nullable=True),
        sa.Column("orgc_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sharing_group_id", sa.Integer(), nullable=True),
        sa.Column("proposal_email_lock", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("publish_timestamp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sighting_timestamp", sa.Integer(), nullable=True),
        sa.Column("disable_correlation", sa.Boolean(), nullable=True),
        sa.Column("extends_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("protected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Revert feeds.event_uuid back to event_id INTEGER
    op.drop_column("feeds", "event_uuid")
    op.add_column("feeds", sa.Column("event_id", sa.Integer(), nullable=True))

    # Revert object_references, event_tags, attribute_tags
    op.drop_column("object_references", "event_uuid")
    op.add_column("object_references", sa.Column("event_id", sa.Integer(), nullable=False))
    op.drop_column("event_tags", "event_uuid")
    op.add_column("event_tags", sa.Column("event_id", sa.Integer(), nullable=True))
    op.drop_column("attribute_tags", "event_uuid")
    op.add_column("attribute_tags", sa.Column("event_id", sa.Integer(), nullable=True))
