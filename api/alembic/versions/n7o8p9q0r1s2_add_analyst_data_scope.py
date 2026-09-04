"""add analyst_data read scope to existing roles

Analyst data (notes, opinions, relationships) is captured on server pull and
feed fetch and read through /analyst-data. Roles store their scopes explicitly,
so the ones that already read reports are granted the equivalent read on
analyst data. The admin role holds "*" and needs nothing.

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "n7o8p9q0r1s2"
down_revision = "m6n7o8p9q0r1"
branch_labels = None
depends_on = None

# Granted to any role that can already read reports: analyst data is
# event-adjacent commentary and carries the same sensitivity.
_SCOPE = "analyst_data:read"

# Roles holding a whole-namespace wildcard get one too, so a later
# analyst_data:create lands without a second migration.
_WILDCARD_SCOPE = "analyst_data:*"


def upgrade():
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("scopes", JSONB))
    connection = op.get_bind()

    for role_id, scopes in connection.execute(
        sa.select(roles.c.id, roles.c.scopes)
    ).fetchall():
        if not isinstance(scopes, list) or "*" in scopes:
            continue

        # Mirror however the role already expresses its reports access.
        if "reports:*" in scopes:
            scope = _WILDCARD_SCOPE
        elif "reports:read" in scopes:
            scope = _SCOPE
        else:
            continue

        if scope in scopes:
            continue

        connection.execute(
            roles.update().where(roles.c.id == role_id).values(scopes=scopes + [scope])
        )


def downgrade():
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("scopes", JSONB))
    connection = op.get_bind()

    for role_id, scopes in connection.execute(
        sa.select(roles.c.id, roles.c.scopes)
    ).fetchall():
        if not isinstance(scopes, list):
            continue

        remaining = [s for s in scopes if s not in (_SCOPE, _WILDCARD_SCOPE)]
        if len(remaining) == len(scopes):
            continue

        connection.execute(
            roles.update().where(roles.c.id == role_id).values(scopes=remaining)
        )
