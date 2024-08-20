"""add feeds table

Revision ID: 541fabd34b80
Revises: 91874c0f72a0
Create Date: 2024-08-13 07:43:21.837336

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Float
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "541fabd34b80"
down_revision = "91874c0f72a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feeds",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False, default={}),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "distribution",
            postgresql.ENUM(name="distribution_level", create_type=False),
            nullable=False,
        ),
        sa.Column("sharing_group_id", sa.Integer(), nullable=True),
        sa.Column("tag_id", sa.Integer(), nullable=True),
        sa.Column("default", sa.Boolean(), default=False),
        sa.Column("source_format", sa.String(255), nullable=False),
        sa.Column("fixed_event", sa.Boolean(), default=False),
        sa.Column("delta_merge", sa.Boolean(), default=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("publish", sa.Boolean(), default=False),
        sa.Column("override_ids", sa.Boolean(), default=False),
        sa.Column("settings", sa.JSON(), nullable=False, default={}),
        sa.Column("input_source", sa.String(255), nullable=False),
        sa.Column("delete_local_file", sa.Boolean(), default=False),
        sa.Column("lookup_visible", sa.Boolean(), default=False),
        sa.Column("headers", sa.JSON(), nullable=False, default={}),
        sa.Column("caching_enabled", sa.Boolean(), default=False),
        sa.Column("force_to_ids", sa.Boolean(), default=False),
        sa.Column("orgc_id", sa.Integer(), nullable=True),
        sa.Column("tag_collection_id", sa.Integer(), nullable=True),
        sa.Column("cached_elements", sa.Integer(), nullable=False, default=0),
        sa.Column("coverage_by_other_feeds", Float(), nullable=False, default=0),
        sa.ForeignKeyConstraint(["sharing_group_id"], ["sharing_groups.id"]),
        sa.ForeignKeyConstraint(["orgc_id"], ["organisations.id"]),
    )


def downgrade():
    op.drop_table("feeds")
