"""grant analyst data write scopes to existing roles

n7o8p9q0r1s2 granted analyst_data:read only, because the write endpoints did
not exist yet. It has already been applied on running instances -- the API
container runs `alembic upgrade head` on start -- so the write scopes need a
migration of their own rather than an edit to that one.

Idempotent: on a fresh install the role seed already carries these scopes and
this becomes a no-op.

Revision ID: o8p9q0r1s2t3
Revises: n7o8p9q0r1s2
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "o8p9q0r1s2t3"
down_revision = "n7o8p9q0r1s2"
branch_labels = None
depends_on = None

# Each role gets the analyst equivalent of the reports access it already holds,
# so a role that can write reports can write analyst data.
_SCOPE_FOR_REPORTS_SCOPE = {
    "reports:create": "analyst_data:create",
    "reports:update": "analyst_data:update",
    "reports:delete": "analyst_data:delete",
}

_WRITE_SCOPES = set(_SCOPE_FOR_REPORTS_SCOPE.values())


def upgrade():
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("scopes", JSONB))
    connection = op.get_bind()

    for role_id, scopes in connection.execute(
        sa.select(roles.c.id, roles.c.scopes)
    ).fetchall():
        # "*" and "analyst_data:*" already cover the write scopes.
        if not isinstance(scopes, list) or "*" in scopes or "analyst_data:*" in scopes:
            continue

        missing = [
            analyst_scope
            for reports_scope, analyst_scope in _SCOPE_FOR_REPORTS_SCOPE.items()
            if reports_scope in scopes and analyst_scope not in scopes
        ]

        if not missing:
            continue

        connection.execute(
            roles.update().where(roles.c.id == role_id).values(scopes=scopes + missing)
        )


def downgrade():
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("scopes", JSONB))
    connection = op.get_bind()

    for role_id, scopes in connection.execute(
        sa.select(roles.c.id, roles.c.scopes)
    ).fetchall():
        if not isinstance(scopes, list):
            continue

        remaining = [scope for scope in scopes if scope not in _WRITE_SCOPES]
        if len(remaining) == len(scopes):
            continue

        connection.execute(
            roles.update().where(roles.c.id == role_id).values(scopes=remaining)
        )
