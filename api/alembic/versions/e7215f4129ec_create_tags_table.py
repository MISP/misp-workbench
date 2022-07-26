"""create tags table

Revision ID: e7215f4129ec
Revises: fcb4b201d20b
Create Date: 2022-07-26 09:18:01.757879

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e7215f4129ec"
down_revision = "fcb4b201d20b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("colour", sa.String(7), nullable=False),
        sa.Column("exportable", sa.Boolean(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hide_tag", sa.Boolean(), nullable=False, default=False),
        sa.Column("numerical_value", sa.Integer()),
        sa.Column("is_galaxy", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_custom_galaxy", sa.Boolean(), nullable=False, default=False),
        sa.Column("local_only", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organisations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
    )

    op.create_index(
        op.f("ix_tags_name"),
        "tags",
        ["name"],
        unique=False,
    )

    op.create_index(
        op.f("ix_tags_org_id"),
        "tags",
        ["org_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_tags_user_id"),
        "tags",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_tags_numerical_value"),
        "tags",
        ["numerical_value"],
        unique=False,
    )

    op.create_table(
        "attribute_tags",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("local", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(
            ["attribute_id"],
            ["attributes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
    )

    op.create_index(
        op.f("ix_attribute_tags_attribute_id"),
        "attribute_tags",
        ["attribute_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_attribute_tags_event_id"),
        "attribute_tags",
        ["event_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_attribute_tags_tag_id"),
        "attribute_tags",
        ["tag_id"],
        unique=False,
    )

    op.create_table(
        "event_tags",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("local", sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
        ),
    )

    op.create_index(
        op.f("ix_event_tags_event_id"),
        "event_tags",
        ["event_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_event_tags_tag_id"),
        "event_tags",
        ["tag_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_index(op.f("ix_tags_org_id"), table_name="tags")
    op.drop_index(op.f("ix_tags_user_id"), table_name="tags")
    op.drop_index(op.f("ix_tags_numerical_value"), table_name="tags")
    op.drop_table("tags")

    op.drop_index(op.f("ix_attribute_tags_attribute_id"), table_name="attribute_tags")
    op.drop_index(op.f("ix_attribute_tags_event_id"), table_name="attribute_tags")
    op.drop_index(op.f("ix_attribute_tags_tag_id"), table_name="attribute_tags")
    op.drop_table("attribute_tags")

    op.drop_index(op.f("ix_event_tags_event_id"), table_name="event_tags")
    op.drop_index(op.f("ix_event_tags_tag_id"), table_name="event_tags")
    op.drop_table("event_tags")
