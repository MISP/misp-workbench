"""add indexes to the galaxy tables

The galaxy tables were created without any index, so importing galaxies and
loading a galaxy's clusters or a cluster's elements scanned whole tables
(~55k clusters, ~275k elements with the bundled misp-galaxy).

The uuid indexes are not unique: databases populated by the previous importer
can hold the same cluster, or galaxy, more than once.

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
"""

from alembic import op

revision = "s2t3u4v5w6x7"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None

INDEXES = [
    ("galaxies", "uuid"),
    ("galaxy_clusters", "uuid"),
    ("galaxy_clusters", "galaxy_id"),
    ("galaxy_elements", "galaxy_cluster_id"),
    ("galaxy_cluster_relations", "galaxy_cluster_id"),
]


def upgrade():
    for table, column in INDEXES:
        op.create_index(
            op.f(f"ix_{table}_{column}"), table, [column], if_not_exists=True
        )


def downgrade():
    for table, column in INDEXES:
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table, if_exists=True)
