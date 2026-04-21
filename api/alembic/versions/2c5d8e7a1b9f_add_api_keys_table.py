"""add api_keys table

Revision ID: 2c5d8e7a1b9f
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-21 00:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

_API_KEY_SCOPES = ["api_keys:read", "api_keys:create", "api_keys:delete"]

# revision identifiers, used by Alembic.
revision = "2c5d8e7a1b9f"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hashed_token", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("scopes", JSONB, nullable=False, server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "disabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index(
        "ix_api_keys_hashed_token", "api_keys", ["hashed_token"], unique=True
    )

    # Grant api_keys:* scopes to existing roles so any user can manage their own keys.
    # Roles with "*" or "api_keys:*" already match, so they are left untouched.
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE roles
            SET scopes = scopes || CAST(:new_scopes AS jsonb)
            WHERE NOT (scopes @> CAST(:new_scopes AS jsonb))
              AND NOT (scopes @> '["*"]'::jsonb)
              AND NOT (scopes @> '["api_keys:*"]'::jsonb)
            """
        ),
        {"new_scopes": json.dumps(_API_KEY_SCOPES)},
    )


def downgrade():
    op.drop_index("ix_api_keys_hashed_token", table_name="api_keys")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_table("api_keys")
