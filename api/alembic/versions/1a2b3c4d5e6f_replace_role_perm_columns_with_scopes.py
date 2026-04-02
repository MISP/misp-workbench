"""replace role perm_* columns with scopes json

Revision ID: 1a2b3c4d5e6f
Revises: e1a2b3c4d5f6
Create Date: 2026-04-01 00:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e6f"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None

_PERM_COLUMNS = [
    "perm_add",
    "perm_modify",
    "perm_modify_org",
    "perm_publish",
    "perm_delegate",
    "perm_sync",
    "perm_admin",
    "perm_audit",
    "perm_full",
    "perm_auth",
    "perm_site_admin",
    "perm_regexp_access",
    "perm_tagger",
    "perm_template",
    "perm_sharing_group",
    "perm_tag_editor",
    "perm_sighting",
    "perm_object_template",
    "perm_galaxy_editor",
    "perm_warninglist",
    "perm_publish_zmq",
    "perm_publish_kafka",
    "perm_decaying",
    "restricted_to_site_admin",
    "enforce_rate_limit",
    "rate_limit_count",
    "memory_limit",
    "max_execution_time",
]

# Scopes for the standard default roles
_USER_SCOPES = [
    "auth:login",
    "events:read",
    "events:create",
    "events:update",
    "events:tag",
    "attributes:read",
    "attributes:create",
    "attributes:update",
    "attributes:delete",
    "attributes:tag",
    "objects:read",
    "objects:create",
    "objects:update",
    "objects:delete",
    "tags:read",
    "tags:create",
    "feeds:read",
    "servers:read",
    "galaxies:read",
    "taxonomies:read",
    "reports:read",
    "reports:create",
    "reports:update",
    "reports:delete",
    "reports:tag",
    "correlations:read",
    "notifications:read",
    "notifications:update",
    "modules:read",
    "modules:query",
    "hunts:read",
    "hunts:create",
    "hunts:update",
    "hunts:delete",
    "hunts:run",
    "sightings:read",
    "sightings:create",
    "attachments:download",
    "attachments:upload",
    "sharing_groups:read",
    "roles:read",
    "organisations:read",
    "users:me",
    "user_settings:read",
    "user_settings:update"
]

_DEFAULT_ROLE_SCOPES = {
    1: ["*"],  # admin
    2: [  # Org Admin
        "auth:login",
        "users:*",
        "events:*",
        "attributes:*",
        "objects:*",
        "servers:*",
        "feeds:*",
        "roles:*",
        "sharing_groups:*",
        "tags:*",
        "modules:*",
        "taxonomies:*",
        "galaxies:*",
        "attachments:*",
        "tasks:*",
        "workers:*",
        "correlations:*",
        "settings:*",
        "hunts:*",
        "notifications:*",
        "mcp:*",
        "organisations:*",
        "reports:*",
        "sightings:*",
    ],
    3: _USER_SCOPES,  # User (default role)
    4: _USER_SCOPES + ["events:delete", "events:publish", "feeds:fetch"],  # Publisher
    5: _USER_SCOPES  # Sync user
    + [
        "events:delete",
        "events:publish",
        "feeds:fetch",
        "servers:pull",
        "servers:push",
        "servers:test",
        "servers:events_index",
        "sharing_groups:create",
        "sharing_groups:update",
        "sharing_groups:delete",
    ],
    6: [  # Read Only
        "auth:login",
        "events:read",
        "attributes:read",
        "objects:read",
        "feeds:read",
        "servers:read",
        "galaxies:read",
        "taxonomies:read",
        "reports:read",
        "correlations:read",
        "notifications:read",
        "modules:read",
        "hunts:read",
        "sightings:read",
        "sharing_groups:read",
        "roles:read",
        "organisations:read",
        "users:me",
        "user_settings:read",
        "user_settings:update"
    ],
}


def upgrade():
    op.add_column(
        "roles",
        sa.Column(
            "scopes",
            JSONB,
            nullable=False,
            server_default="[]",
        ),
    )

    conn = op.get_bind()
    for role_id, scopes in _DEFAULT_ROLE_SCOPES.items():
        conn.execute(
            sa.text("UPDATE roles SET scopes = :scopes WHERE id = :id"),
            {"scopes": json.dumps(scopes), "id": role_id},
        )

    for col in _PERM_COLUMNS:
        op.drop_column("roles", col)


def downgrade():
    op.add_column(
        "roles",
        sa.Column("perm_add", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column("perm_modify", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_modify_org", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_publish", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_delegate", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column("perm_sync", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column("perm_admin", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column("perm_audit", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column("perm_full", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column("perm_auth", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_site_admin", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_regexp_access", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column("perm_tagger", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_template", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_sharing_group", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_tag_editor", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_sighting", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_object_template",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_galaxy_editor", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_warninglist", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_publish_zmq", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_publish_kafka", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "perm_decaying", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "restricted_to_site_admin",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "enforce_rate_limit", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "roles",
        sa.Column(
            "rate_limit_count", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "roles",
        sa.Column("memory_limit", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "roles",
        sa.Column(
            "max_execution_time", sa.String(255), nullable=False, server_default=""
        ),
    )

    op.drop_column("roles", "scopes")
