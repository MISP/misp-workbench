"""add alert receivers

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-14 18:00:00.000000

Inbound alert webhooks: SIEM and SOAR alerts, mapped to sightings. With the
alert_receivers:read scope for Org Admin, User, Publisher and Read Only, and
alert_receivers:manage for Org Admin and Publisher.

"""

import json

import sqlalchemy as sa
from alembic import op

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None

_SCOPES = {
    "alert_receivers:read": [2, 3, 4, 6],
    "alert_receivers:manage": [2, 4],
}


def upgrade():
    op.create_table(
        "alert_receivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organisations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preset", sa.String(32), nullable=False, server_default="generic"),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("only_known", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rate_limit", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allowed_ips", sa.JSON(), nullable=False),
        sa.Column("token_prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ip", sa.String(64), nullable=True),
        sa.Column("received_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sightings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_payload", sa.Text(), nullable=True),
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
    op.create_index("ix_alert_receivers_id", "alert_receivers", ["id"])
    op.create_index("ix_alert_receivers_org_id", "alert_receivers", ["org_id"])
    op.create_index(
        "ix_alert_receivers_token_hash", "alert_receivers", ["token_hash"], unique=True
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
    op.drop_index("ix_alert_receivers_token_hash", table_name="alert_receivers")
    op.drop_index("ix_alert_receivers_org_id", table_name="alert_receivers")
    op.drop_index("ix_alert_receivers_id", table_name="alert_receivers")
    op.drop_table("alert_receivers")
