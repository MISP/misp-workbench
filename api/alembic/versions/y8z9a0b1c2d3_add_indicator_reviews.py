"""add indicator reviews

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-10-13 12:00:00.000000

The review queue: analysts' decisions on indicators, auto-approve profiles,
the indicators:review scope (Org Admin and Publisher), and a starting
auto-approve profile for the trusted bulk.

"""

import json
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "y8z9a0b1c2d3"
down_revision = "x7y8z9a0b1c2"
branch_labels = None
depends_on = None

# Built-in roles (see 1a2b3c4d5e6f): Org Admin and Publisher decide what
# reaches security controls.
_REVIEW_ROLES = [2, 4]
_SCOPES = ["indicators:review"]

_SEED = {
    "name": "Auto-approve: trusted sources",
    "description": (
        "Approves without a review what a trusted source (score modifier 10 "
        "or more) reports with a score of 70 or more, flagged for IDS, not "
        "on a warninglist and without validation issues."
    ),
    "granularity": "indicators",
    "auto_approve": True,
    "rules": {
        "to_ids": True,
        "min_score": 70,
        "min_source_trust": 10,
        "exclude_warninglisted": True,
        "exclude_validation_issues": True,
    },
}


def upgrade():
    op.create_table(
        "indicator_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("indicator_uuid", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "warninglisted", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_indicator_reviews_id", "indicator_reviews", ["id"])
    op.create_index(
        "ix_indicator_reviews_indicator_uuid",
        "indicator_reviews",
        ["indicator_uuid"],
        unique=True,
    )
    op.create_index("ix_indicator_reviews_status", "indicator_reviews", ["status"])
    op.create_index("ix_indicator_reviews_user_id", "indicator_reviews", ["user_id"])
    op.create_index(
        "ix_indicator_reviews_decided_at", "indicator_reviews", ["decided_at"]
    )

    op.add_column(
        "detection_profiles",
        sa.Column("auto_approve", sa.Boolean(), nullable=False, server_default="false"),
    )

    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM detection_profiles WHERE name = :name"),
        {"name": _SEED["name"]},
    ).first()
    if not exists:
        conn.execute(
            sa.text("""
                INSERT INTO detection_profiles
                    (name, description, granularity, rules, auto_approve, created_at)
                VALUES
                    (:name, :description, :granularity, CAST(:rules AS json),
                     :auto_approve, :created_at)
                """),
            {
                **_SEED,
                "rules": json.dumps(_SEED["rules"]),
                "created_at": datetime.now(timezone.utc),
            },
        )

    for role_id in _REVIEW_ROLES:
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
    for role_id in _REVIEW_ROLES:
        for scope in _SCOPES:
            conn.execute(
                sa.text(
                    "UPDATE roles SET scopes = scopes - :scope WHERE id = :role_id"
                ),
                {"scope": scope, "role_id": role_id},
            )
    op.drop_column("detection_profiles", "auto_approve")
    op.drop_index("ix_indicator_reviews_decided_at", table_name="indicator_reviews")
    op.drop_index("ix_indicator_reviews_user_id", table_name="indicator_reviews")
    op.drop_index("ix_indicator_reviews_status", table_name="indicator_reviews")
    op.drop_index("ix_indicator_reviews_indicator_uuid", table_name="indicator_reviews")
    op.drop_index("ix_indicator_reviews_id", table_name="indicator_reviews")
    op.drop_table("indicator_reviews")
