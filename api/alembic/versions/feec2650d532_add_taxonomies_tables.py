"""add taxonomies tables

Revision ID: feec2650d532
Revises: 541fabd34b80
Create Date: 2024-11-28 10:09:50.801106

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "feec2650d532"
down_revision = "541fabd34b80"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "taxonomies",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("namespace", sa.String(255), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("exclusive", sa.Boolean(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("highlighted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("namespace"),
    )
    op.create_table(
        "taxonomy_predicates",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("taxonomy_id", sa.Integer, index=True, nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("expanded", sa.String()),
        sa.Column("colour", sa.String(7)),
        sa.Column("description", sa.String()),
        sa.Column("exclusive", sa.Boolean(), nullable=False),
        sa.Column("numerical_value", sa.Integer, index=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "taxonomy_entries",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("taxonomy_predicate_id", sa.Integer, index=True, nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("expanded", sa.String()),
        sa.Column("colour", sa.String(7)),
        sa.Column("description", sa.String()),
        sa.Column("numerical_value", sa.Integer, index=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("taxonomy_entry")
    op.drop_table("taxonomy_predicates")
    op.drop_table("taxonomies")
