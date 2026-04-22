"""grant api_keys scopes to default roles

Targets only the built-in default role ids seeded by
1a2b3c4d5e6f_replace_role_perm_columns_with_scopes.py (2=Org Admin,
3=User, 4=Publisher, 5=Sync user, 6=Read Only). Custom roles are left
untouched; operators who want those to mint API keys must opt in via
the roles API.

Revision ID: 4a5b6c7d8e9f
Revises: 3d6e9f8c2a1b
Create Date: 2026-04-22 10:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4a5b6c7d8e9f"
down_revision = "3d6e9f8c2a1b"
branch_labels = None
depends_on = None


_FULL_API_KEY_SCOPES = [
    "api_keys:read",
    "api_keys:create",
    "api_keys:update",
    "api_keys:delete",
]
_READONLY_API_KEY_SCOPES = ["api_keys:read"]

# Role 1 (admin) already has "*" and is intentionally skipped.
_ROLE_SCOPE_GRANTS = {
    2: _FULL_API_KEY_SCOPES,  # Org Admin
    3: _FULL_API_KEY_SCOPES,  # User
    4: _FULL_API_KEY_SCOPES,  # Publisher
    5: _FULL_API_KEY_SCOPES,  # Sync user
    6: _READONLY_API_KEY_SCOPES,  # Read Only — can inspect its own keys only
}


def upgrade():
    conn = op.get_bind()
    for role_id, scopes in _ROLE_SCOPE_GRANTS.items():
        conn.execute(
            sa.text(
                """
                UPDATE roles
                SET scopes = scopes || CAST(:new_scopes AS jsonb)
                WHERE id = :role_id
                  AND NOT (scopes @> CAST(:new_scopes AS jsonb))
                  AND NOT (scopes @> '["*"]'::jsonb)
                """
            ),
            {"new_scopes": json.dumps(scopes), "role_id": role_id},
        )


def downgrade():
    conn = op.get_bind()
    for role_id, scopes in _ROLE_SCOPE_GRANTS.items():
        for scope in scopes:
            conn.execute(
                sa.text(
                    """
                    UPDATE roles
                    SET scopes = scopes - :scope
                    WHERE id = :role_id
                    """
                ),
                {"scope": scope, "role_id": role_id},
            )
