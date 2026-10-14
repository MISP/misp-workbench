"""add external dynamic lists

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-10-14 16:00:00.000000

External dynamic lists (a detection profile's IPs, domains, URLs or hashes,
in a firewall vendor's format) and their URL tokens, with the edls:read
scope for Org Admin, User, Publisher and Read Only, and edls:manage for Org
Admin and Publisher.

"""

import json

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None

_SCOPES = {
    "edls:read": [2, 3, 4, 6],
    "edls:manage": [2, 4],
}


def upgrade():
    op.create_table(
        "edls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("detection_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("list_type", sa.String(20), nullable=False),
        sa.Column("vendor", sa.String(20), nullable=False),
        sa.Column("max_entries", sa.Integer(), nullable=True),
        sa.Column(
            "include_subdomains",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("refresh_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("entry_count", sa.Integer(), nullable=True),
        sa.Column("truncated", sa.Integer(), nullable=True),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("build_error", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("org_id", "name"),
    )
    op.create_index("ix_edls_id", "edls", ["id"])
    op.create_index("ix_edls_org_id", "edls", ["org_id"])
    op.create_index("ix_edls_profile_id", "edls", ["profile_id"])

    op.create_table(
        "edl_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "edl_id",
            sa.Integer(),
            sa.ForeignKey("edls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("allowed_ips", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(64), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_edl_tokens_id", "edl_tokens", ["id"])
    op.create_index("ix_edl_tokens_edl_id", "edl_tokens", ["edl_id"])
    op.create_index(
        "ix_edl_tokens_token_hash", "edl_tokens", ["token_hash"], unique=True
    )

    conn = op.get_bind()
    for scope, role_ids in _SCOPES.items():
        for role_id in role_ids:
            conn.execute(
                sa.text("""
                    UPDATE roles
                    SET scopes = scopes || CAST(:new_scopes AS jsonb)
                    WHERE id = :role_id
                      AND NOT (scopes @> CAST(:new_scopes AS jsonb))
                      AND NOT (scopes @> '["*"]'::jsonb)
                    """),
                {"new_scopes": json.dumps([scope]), "role_id": role_id},
            )


def downgrade():
    conn = op.get_bind()
    for scope, role_ids in _SCOPES.items():
        for role_id in role_ids:
            conn.execute(
                sa.text(
                    "UPDATE roles SET scopes = scopes - :scope WHERE id = :role_id"
                ),
                {"scope": scope, "role_id": role_id},
            )
    op.drop_index("ix_edl_tokens_token_hash", table_name="edl_tokens")
    op.drop_index("ix_edl_tokens_edl_id", table_name="edl_tokens")
    op.drop_index("ix_edl_tokens_id", table_name="edl_tokens")
    op.drop_table("edl_tokens")
    op.drop_index("ix_edls_profile_id", table_name="edls")
    op.drop_index("ix_edls_org_id", table_name="edls")
    op.drop_index("ix_edls_id", table_name="edls")
    op.drop_table("edls")
