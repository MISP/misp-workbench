"""add galaxies tables

Revision ID: 39cbeba07d8b
Revises: feec2650d532
Create Date: 2024-12-12 09:34:45.897961

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "39cbeba07d8b"
down_revision = "feec2650d532"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "galaxies",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("uuid", sa.types.Uuid(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(255), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("icon", sa.String(255), nullable=False),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("local_only", sa.Boolean(), nullable=False),
        sa.Column("kill_chain_order", sa.JSON(), nullable=True, default={}),
        sa.Column("default", sa.Boolean(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("orgc_id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime()),
        sa.Column("modified", sa.DateTime()),
        sa.Column(
            "distribution",
            postgresql.ENUM(name="distribution_level", create_type=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organisations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["orgc_id"],
            ["organisations.id"],
        ),
    )

    op.create_table(
        "galaxy_clusters",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("uuid", sa.types.Uuid(as_uuid=False), nullable=False),
        sa.Column("collection_uuid", sa.types.Uuid(as_uuid=False), nullable=True),
        sa.Column("type", sa.String(255), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("tag_name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("galaxy_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("authors", sa.JSON(), nullable=False, default={}),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column(
            "distribution",
            postgresql.ENUM(name="distribution_level", create_type=False),
            nullable=False,
        ),
        sa.Column("sharing_group_id", sa.Integer(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("orgc_id", sa.Integer(), nullable=False),
        sa.Column("extends_uuid", sa.types.Uuid(as_uuid=False), nullable=True),
        sa.Column("extends_version", sa.Integer(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["galaxy_id"],
            ["galaxies.id"],
        ),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organisations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["orgc_id"],
            ["organisations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sharing_group_id"],
            ["sharing_groups.id"],
        ),
    )

    op.create_table(
        "galaxy_elements",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("galaxy_cluster_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["galaxy_cluster_id"],
            ["galaxy_clusters.id"],
        ),
    )

    op.create_table(
        "galaxy_cluster_relations",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("galaxy_cluster_id", sa.Integer(), nullable=False),
        sa.Column("referenced_galaxy_cluster_id", sa.Integer(), nullable=True),
        sa.Column(
            "referenced_galaxy_cluster_uuid",
            sa.types.Uuid(as_uuid=False),
            nullable=False,
        ),
        sa.Column("referenced_galaxy_cluster_type", sa.String(255), nullable=False),
        sa.Column("galaxy_cluster_uuid", sa.types.Uuid(as_uuid=False), nullable=False),
        sa.Column(
            "distribution",
            postgresql.ENUM(name="distribution_level", create_type=False),
            nullable=False,
        ),
        sa.Column("sharing_group_id", sa.Integer(), nullable=True),
        sa.Column("default", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["galaxy_cluster_id"],
            ["galaxy_clusters.id"],
        ),
        sa.ForeignKeyConstraint(
            ["sharing_group_id"],
            ["sharing_groups.id"],
        ),
    )

    op.create_table(
        "galaxy_cluster_relation_tags",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("galaxy_cluster_relation_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["galaxy_cluster_relation_id"],
            ["galaxy_cluster_relations.id"],
        ),
    )

    op.create_table(
        "galaxy_cluster_blocklists",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("cluster_uuid", sa.types.Uuid(as_uuid=False), nullable=False),
        sa.Column("created", sa.DateTime()),
        sa.Column("cluster_info", sa.String(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("cluster_orgc", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("galaxy_cluster_blocklists")
    op.drop_table("galaxy_cluster_relation_tags")
    op.drop_table("galaxy_cluster_relations")
    op.drop_table("galaxy_elements")
    op.drop_table("galaxy_clusters")
    op.drop_table("galaxies")
