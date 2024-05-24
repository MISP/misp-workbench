"""add servers table

Revision ID: 189781eabdc4
Revises: 939b47ef27e5
Create Date: 2022-05-25 16:35:14.812051

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "189781eabdc4"
down_revision = "939b47ef27e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("authkey", sa.String(255), nullable=False),  # TODO: encrypt
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("push", sa.Boolean(), nullable=False, default=False),
        sa.Column("pull", sa.Boolean(), nullable=False, default=False),
        sa.Column("push_sightings", sa.Boolean(), nullable=False, default=False),
        sa.Column("push_galaxy_clusters", sa.Boolean(), nullable=False, default=False),
        sa.Column("pull_galaxy_clusters", sa.Boolean(), nullable=False, default=False),
        sa.Column("last_pulled_id", sa.Integer()),
        sa.Column("last_pushed_id", sa.Integer()),
        sa.Column("organisation", sa.String(255)),
        sa.Column("remote_org_id", sa.Integer(), nullable=False),
        sa.Column("publish_without_email", sa.Boolean(), nullable=False, default=False),
        sa.Column("unpublish_event", sa.Boolean(), nullable=False, default=False),
        sa.Column("self_signed", sa.Boolean(), nullable=False, default=False),
        sa.Column("pull_rules", sa.JSON(), nullable=False, default={}),
        sa.Column("push_rules", sa.JSON(), nullable=False, default={}),
        sa.Column("cert_file", sa.String(255)),
        sa.Column("client_cert_file", sa.String(255)),
        sa.Column("internal", sa.Boolean(), nullable=False, default=False),
        sa.Column("skip_proxy", sa.Boolean(), nullable=False, default=False),
        sa.Column("caching_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
    )


def downgrade():
    op.drop_table("servers")
