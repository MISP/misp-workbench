"""add the change preview and approval gate

Revision ID: z9a0b1c2d3e4
Revises: y8z9a0b1c2d3
Create Date: 2026-10-13 14:00:00.000000

A detection profile's approval gate, the record of its change checks
(profile_releases), and when feeds and servers were added (unknown for the
existing ones), so additions from a very new source can be flagged.

"""

import sqlalchemy as sa
from alembic import op

revision = "z9a0b1c2d3e4"
down_revision = "y8z9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("detection_profiles", sa.Column("gate", sa.JSON(), nullable=True))
    op.create_table(
        "profile_releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("detection_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("members", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("removed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_profile_releases_id", "profile_releases", ["id"])
    op.create_index(
        "ix_profile_releases_profile_id", "profile_releases", ["profile_id"]
    )
    op.create_index(
        "ix_profile_releases_created_at", "profile_releases", ["created_at"]
    )
    op.add_column(
        "feeds", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "servers", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("servers", "created_at")
    op.drop_column("feeds", "created_at")
    op.drop_index("ix_profile_releases_created_at", table_name="profile_releases")
    op.drop_index("ix_profile_releases_profile_id", table_name="profile_releases")
    op.drop_index("ix_profile_releases_id", table_name="profile_releases")
    op.drop_table("profile_releases")
    op.drop_column("detection_profiles", "gate")
