"""add detection profiles

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-10-13 00:00:00.000000

Named detection profiles shared by all outputs, an export's reference to one,
the detection_profiles:* scopes (read for the built-in non-admin roles), and
two starting profiles.

"""

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "x7y8z9a0b1c2"
down_revision = "w6x7y8z9a0b1"
branch_labels = None
depends_on = None

# Built-in roles (see 1a2b3c4d5e6f): everyone can use profiles; changing them
# stays with admins ("*").
_READ_ROLES = [2, 3, 4, 5, 6]
_SCOPES = ["detection_profiles:read"]

_SEED = [
    {
        "name": "SIEM alerting",
        "description": (
            "Indicators worth alerting on: flagged for IDS, scored 50 or more, "
            "not on a warninglist, no validation issues, TLP amber or less."
        ),
        "granularity": "indicators",
        "rules": {
            "to_ids": True,
            "min_score": 50,
            "tlp_ceiling": "tlp:amber",
            "exclude_warninglisted": True,
            "exclude_validation_issues": True,
        },
    },
    {
        "name": "Firewall block list",
        "description": (
            "Network indicators safe to block: IPs, domains, hostnames and URLs "
            "flagged for IDS, scored 70 or more, seen in the last 90 days, not "
            "on a warninglist, no validation issues, TLP amber or less."
        ),
        "granularity": "indicators",
        "rules": {
            "types": ["ip-src", "ip-dst", "domain", "hostname", "url"],
            "to_ids": True,
            "min_score": 70,
            "max_age_days": 90,
            "tlp_ceiling": "tlp:amber",
            "exclude_warninglisted": True,
            "exclude_validation_issues": True,
        },
    },
]


def upgrade():
    profiles = op.create_table(
        "detection_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "granularity",
            sa.String(length=16),
            nullable=False,
            server_default="indicators",
        ),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_detection_profiles_id", "detection_profiles", ["id"])
    op.add_column(
        "exports",
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("detection_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_exports_profile_id", "exports", ["profile_id"])

    now = datetime.now(timezone.utc)
    op.bulk_insert(profiles, [{**p, "created_at": now} for p in _SEED])

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
    op.drop_index("ix_exports_profile_id", table_name="exports")
    op.drop_column("exports", "profile_id")
    op.drop_index("ix_detection_profiles_id", table_name="detection_profiles")
    op.drop_table("detection_profiles")
