"""add organisation warninglists

Revision ID: a0b1c2d3e4f5
Revises: z9a0b1c2d3e4
Create Date: 2026-10-14 10:00:00.000000

Warninglists an organisation keeps for itself (its ranges, domains,
partners), with entries of their own (values, CIDRs, domain suffixes,
regexes, each with a comment and an optional expiry), an optional source
URL to sync them from, and the local_warninglists:manage scope for Org
Admin and Publisher.

"""

import json

import sqlalchemy as sa
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "z9a0b1c2d3e4"
branch_labels = None
depends_on = None

_MANAGE_ROLES = [2, 4]
_SCOPES = ["local_warninglists:manage"]


def upgrade():
    op.add_column(
        "warninglists",
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_warninglists_org_id", "warninglists", ["org_id"])
    # Names are unique among the MISP lists, and within an organisation: two
    # organisations can both keep a "Corporate ranges", and a list named like
    # a MISP one is never mistaken for it.
    op.drop_constraint("warninglists_name_key", "warninglists", type_="unique")
    op.create_index(
        "uq_warninglists_shared_name",
        "warninglists",
        ["name"],
        unique=True,
        postgresql_where=sa.text("org_id IS NULL"),
    )
    op.create_index(
        "uq_warninglists_org_name",
        "warninglists",
        ["org_id", "name"],
        unique=True,
        postgresql_where=sa.text("org_id IS NOT NULL"),
    )
    op.add_column("warninglists", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column(
        "warninglists",
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("warninglists", sa.Column("sync_error", sa.Text(), nullable=True))
    op.create_table(
        "warninglist_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "warninglist_id",
            sa.Integer(),
            sa.ForeignKey("warninglists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        # Added by hand, by an import, or by a sync from the list's URL.
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("warninglist_id", "kind", "value"),
    )
    op.create_index(
        "ix_warninglist_entries_warninglist_id",
        "warninglist_entries",
        ["warninglist_id"],
    )
    op.create_index(
        "ix_warninglist_entries_expires_at", "warninglist_entries", ["expires_at"]
    )

    conn = op.get_bind()
    for role_id in _MANAGE_ROLES:
        conn.execute(
            sa.text("""
                UPDATE roles
                SET scopes = scopes || CAST(:new_scopes AS jsonb)
                WHERE id = :role_id
                  AND NOT (scopes @> CAST(:new_scopes AS jsonb))
                  AND NOT (scopes @> '["*"]'::jsonb)
                """),
            {"new_scopes": json.dumps(_SCOPES), "role_id": role_id},
        )


def downgrade():
    conn = op.get_bind()
    for role_id in _MANAGE_ROLES:
        for scope in _SCOPES:
            conn.execute(
                sa.text(
                    "UPDATE roles SET scopes = scopes - :scope WHERE id = :role_id"
                ),
                {"scope": scope, "role_id": role_id},
            )
    op.drop_index("ix_warninglist_entries_expires_at", table_name="warninglist_entries")
    op.drop_index(
        "ix_warninglist_entries_warninglist_id", table_name="warninglist_entries"
    )
    op.drop_table("warninglist_entries")
    op.drop_column("warninglists", "sync_error")
    op.drop_column("warninglists", "synced_at")
    op.drop_column("warninglists", "source_url")
    op.execute("DELETE FROM warninglists WHERE org_id IS NOT NULL")
    op.drop_index("uq_warninglists_org_name", table_name="warninglists")
    op.drop_index("uq_warninglists_shared_name", table_name="warninglists")
    op.create_unique_constraint("warninglists_name_key", "warninglists", ["name"])
    op.drop_index("ix_warninglists_org_id", table_name="warninglists")
    op.drop_column("warninglists", "org_id")
