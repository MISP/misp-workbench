"""Add sharing groups table

Revision ID: fcb4b201d20b
Revises: 05113716518f
Create Date: 2022-06-21 14:52:30.505311

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "fcb4b201d20b"
down_revision = "05113716518f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "sharing_groups",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("releasability", sa.String()),
        sa.Column("description", sa.String()),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), unique=True),
        sa.Column("organisation_uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("org_id", sa.Integer, nullable=False),
        sa.Column("sync_user_id", sa.Integer, nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("comment", sa.String()),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("modified", sa.DateTime(), nullable=False),
        sa.Column("local", sa.Boolean(), nullable=False),
        sa.Column("roaming", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organisations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sync_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_sharing_groups_org_id"), "sharing_groups", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_sharing_groups_sync_user_id"),
        "sharing_groups",
        ["sync_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sharing_groups_organisation_uuid"),
        "sharing_groups",
        ["organisation_uuid"],
        unique=False,
    )

    op.create_table(
        "sharing_group_orgs",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("sharing_group_id", sa.Integer, nullable=False),
        sa.Column("org_id", sa.Integer, nullable=False),
        sa.Column("extend", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organisations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sharing_group_id"],
            ["sharing_groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sharing_group_orgs_org_id"),
        "sharing_group_orgs",
        ["org_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sharing_group_orgs_sharing_group_id"),
        "sharing_group_orgs",
        ["sharing_group_id"],
        unique=False,
    )

    op.create_table(
        "sharing_group_servers",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("sharing_group_id", sa.Integer, nullable=False),
        sa.Column("server_id", sa.Integer, nullable=False),
        sa.Column("all_orgs", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["servers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sharing_group_id"],
            ["sharing_groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sharing_group_servers_server_id"),
        "sharing_group_servers",
        ["server_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sharing_group_servers_sharing_group_id"),
        "sharing_group_servers",
        ["sharing_group_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_objects_sharing_groups",
        "objects",
        "sharing_groups",
        ["sharing_group_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_events_sharing_groups",
        "events",
        "sharing_groups",
        ["sharing_group_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_attributes_sharing_groups",
        "attributes",
        "sharing_groups",
        ["sharing_group_id"],
        ["id"],
    )


def downgrade():
    op.drop_index(op.f("ix_sharing_groups_org_id"), table_name="sharing_groups")
    op.drop_index(op.f("ix_sharing_groups_sync_user_id"), table_name="sharing_groups")
    op.drop_index(
        op.f("ix_sharing_groups_organisation_uuid"), table_name="sharing_groups"
    )
    op.drop_index(
        op.f("fk_objects_sharing_groups"),
        table_name="sharing_groups",
    )
    op.drop_index(
        op.f("fk_events_sharing_groups"),
        table_name="sharing_groups",
    )
    op.drop_index(
        op.f("fk_attributes_sharing_groups"),
        table_name="sharing_groups",
    )
    op.drop_table("sharing_groups")

    op.drop_index(op.f("ix_sharing_group_orgs_org_id"), table_name="sharing_group_orgs")
    op.drop_index(
        op.f("ix_sharing_group_orgs_sharing_group_id"), table_name="sharing_group_orgs"
    )
    op.drop_table("sharing_group_orgs")

    op.drop_index(
        op.f("ix_sharing_group_servers_org_id"), table_name="sharing_group_servers"
    )
    op.drop_index(
        op.f("ix_sharing_group_servers_sharing_group_id"),
        table_name="sharing_group_servers",
    )

    op.drop_table("sharing_group_servers")
