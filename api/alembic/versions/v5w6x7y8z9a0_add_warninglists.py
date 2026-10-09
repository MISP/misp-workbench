"""add warninglists

Revision ID: v5w6x7y8z9a0
Revises: u4v5w6x7y8z9
Create Date: 2026-10-09 00:00:00.000000

MISP warninglists (metadata; entries live in OpenSearch), and the
warninglists:read scope for the built-in non-admin roles.

"""

import json

import sqlalchemy as sa
from alembic import op

revision = "v5w6x7y8z9a0"
down_revision = "u4v5w6x7y8z9"
branch_labels = None
depends_on = None

# Built-in roles (see 1a2b3c4d5e6f): seeing why a value is flagged is useful
# to everyone; changing which lists apply stays with admins ("*").
_READ_ROLES = [2, 3, 4, 5, 6]
_SCOPES = ["warninglists:read"]


def upgrade():
    op.create_table(
        "warninglists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("matching_attributes", sa.JSON(), nullable=False),
        sa.Column("patterns", sa.JSON(), nullable=True),
        sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_warninglists_id", "warninglists", ["id"])

    conn = op.get_bind()
    for role_id in _READ_ROLES:
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
    for role_id in _READ_ROLES:
        for scope in _SCOPES:
            conn.execute(
                sa.text(
                    "UPDATE roles SET scopes = scopes - :scope WHERE id = :role_id"
                ),
                {"scope": scope, "role_id": role_id},
            )
    op.drop_index("ix_warninglists_id", table_name="warninglists")
    op.drop_table("warninglists")
