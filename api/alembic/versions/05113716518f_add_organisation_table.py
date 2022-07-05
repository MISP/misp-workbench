"""Add organisation table

Revision ID: 05113716518f
Revises: 4d3af7aab04f
Create Date: 2022-06-17 13:51:19.945810

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "05113716518f"
down_revision = "4d3af7aab04f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organisations",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("date_created", sa.DateTime(), nullable=False),
        sa.Column("date_modified", sa.DateTime(), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("type", sa.String(255)),
        sa.Column("nationality", sa.String(255)),
        sa.Column("sector", sa.String(255)),
        sa.Column("created_by", sa.Integer, nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("contacts", sa.String),
        sa.Column("local", sa.Boolean(), nullable=False),
        sa.Column("restricted_to_domain", sa.String),
        sa.Column("landing_page", sa.String),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_organisations_name"), "organisations", ["name"], unique=False
    )

    op.create_foreign_key(
        "fk_users_organisations",
        "users",
        "organisations",
        ["org_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_events_organisations",
        "events",
        "organisations",
        ["org_id"],
        ["id"],
    )


def downgrade():
    op.drop_index(op.f("ix_organisations_name"), table_name="organisations")
    op.drop_index(op.f("fk_users_organisations"), table_name="users")
    op.drop_index(op.f("fk_events_organisations"), table_name="events")
    op.drop_table("organisations")
