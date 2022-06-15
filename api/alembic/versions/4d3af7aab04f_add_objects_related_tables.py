"""Add objects related tables

Revision ID: 4d3af7aab04f
Revises: 189781eabdc4
Create Date: 2022-06-14 13:43:44.464782

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4d3af7aab04f"
down_revision = "189781eabdc4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "objects",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255)),
        sa.Column("meta_category", sa.String(255)),
        sa.Column("description", sa.String()),
        sa.Column("template_uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column("event_id", sa.Integer, nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("timestamp", sa.Integer, nullable=False),
        sa.Column(
            "distribution",
            postgresql.ENUM(name="distribution_level", create_type=False),
            nullable=False,
        ),
        sa.Column("sharing_group_id", sa.Integer()),
        sa.Column("comment", sa.String()),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("first_seen", sa.BigInteger()),
        sa.Column("last_seen", sa.BigInteger()),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(op.f("ix_objects_name"), "objects", ["name"], unique=False)
    op.create_index(
        op.f("ix_objects_template_uuid"), "objects", ["template_uuid"], unique=False
    )
    op.create_index(
        op.f("ix_objects_template_version"),
        "objects",
        ["template_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_objects_meta_category"), "objects", ["meta_category"], unique=False
    )
    op.create_index(op.f("ix_objects_event_id"), "objects", ["event_id"], unique=False)
    op.create_index(
        op.f("ix_objects_timestamp"), "objects", ["timestamp"], unique=False
    )
    op.create_index(
        op.f("ix_objects_distribution"), "objects", ["distribution"], unique=False
    )
    op.create_index(
        op.f("ix_objects_sharing_group_id"),
        "objects",
        ["sharing_group_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_objects_first_seen"), "objects", ["first_seen"], unique=False
    )
    op.create_index(
        op.f("ix_objects_last_seen"), "objects", ["last_seen"], unique=False
    )

    op.create_table(
        "object_relationships",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("format", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_object_relationships_name"),
        "object_relationships",
        ["name"],
        unique=False,
    )

    op.create_table(
        "object_references",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("timestamp", sa.Integer, nullable=False),
        sa.Column("object_id", sa.Integer, nullable=False),
        sa.Column("event_id", sa.Integer, nullable=False),
        sa.Column("source_uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("referenced_uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("referenced_id", sa.Integer, nullable=False),
        sa.Column("referenced_type", sa.Integer, nullable=False),
        sa.Column("relationship_type", sa.String(255)),
        sa.Column("comment", sa.String(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["object_id"],
            ["objects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_object_references_object_id"),
        "object_references",
        ["object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_object_references_referenced_id"),
        "object_references",
        ["referenced_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_object_references_event_id"),
        "object_references",
        ["event_id"],
        unique=False,
    )

    op.create_table(
        "object_templates",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("name", sa.String(255)),
        sa.Column("meta_category", sa.String(255)),
        sa.Column("description", sa.String()),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("requirements", postgresql.JSON, default=lambda: {}),
        sa.Column("fixed", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        # sa.ForeignKeyConstraint(
        #     ["org_id"],
        #     ["organisations.id"],
        # ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_object_templates_user_id"),
        "object_templates",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_object_templates_org_id"), "object_templates", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_object_templates_uuid"), "object_templates", ["uuid"], unique=False
    )
    op.create_index(
        op.f("ix_object_templates_name"), "object_templates", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_object_templates_meta_category"),
        "object_templates",
        ["meta_category"],
        unique=False,
    )

    op.create_table(
        "object_template_elements",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("object_template_id", sa.Integer(), nullable=False),
        sa.Column("object_relation", sa.String(255)),
        sa.Column("type", sa.String(255)),
        sa.Column("ui-priority", sa.Integer, nullable=False),
        sa.Column("categories", postgresql.JSON, default=lambda: []),
        sa.Column("sane_default", postgresql.JSON, default=lambda: []),
        sa.Column("values_list", postgresql.JSON, default=lambda: []),
        sa.Column("description", sa.String()),
        sa.Column("disable_correlation", sa.Boolean()),
        sa.Column("multiple", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["object_template_id"],
            ["object_templates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_object_template_elements_object_relation"),
        "object_template_elements",
        ["object_relation"],
        unique=False,
    )
    op.create_index(
        op.f("ix_object_template_elements_type"),
        "object_template_elements",
        ["type"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_object_references_object_id"), table_name="object_id")
    op.drop_index(
        op.f("ix_object_references_referenced_id"), table_name="referenced_id"
    )
    op.drop_index(op.f("ix_object_references_event_id"), table_name="event_id")
    op.drop_table("object_references")

    op.drop_index(
        op.f("ix_object_relationships_name"), table_name="object_relationships"
    )
    op.drop_table("object_relationships")

    op.drop_index(op.f("ix_objects_name"), table_name="objects")
    op.drop_index(op.f("ix_objects_template_uuid"), table_name="objects")
    op.drop_index(op.f("ix_objects_template_version"), table_name="objects")
    op.drop_index(op.f("ix_objects_meta_category"), table_name="objects")
    op.drop_index(op.f("ix_objects_event_id"), table_name="objects")
    op.drop_index(op.f("ix_objects_timestamp"), table_name="objects")
    op.drop_index(op.f("ix_objects_distribution"), table_name="objects")
    op.drop_index(op.f("ix_objects_sharing_group_id"), table_name="objects")
    op.drop_index(op.f("ix_objects_first_seen"), table_name="objects")
    op.drop_index(op.f("ix_objects_last_seen"), table_name="objects")
    op.drop_table("objects")

    op.drop_index(op.f("ix_object_templates_user_id"), table_name="object_templates")
    op.drop_index(op.f("ix_object_templates_org_id"), table_name="object_templates")
    op.drop_index(op.f("ix_object_templates_uuid"), table_name="object_templates")
    op.drop_index(op.f("ix_object_templates_name"), table_name="object_templates")
    op.drop_index(
        op.f("ix_object_templates_meta_category"), table_name="object_templates"
    )
    op.drop_table("object_templates")

    op.drop_index(
        op.f("ix_object_template_elements_object_relation"),
        table_name="object_templates",
    )
    op.drop_index(
        op.f("ix_object_template_elements_type"), table_name="object_templates"
    )
    op.drop_table("object_template_elements")
