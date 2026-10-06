"""store galaxy cluster tag names as misp-galaxy:<type>="<value>"

Clusters imported from misp-galaxy got a tag_name of misp-galaxy:<type>=<uuid>,
which matches no tag: the tags created when a galaxy is enabled, and the ones
MISP attaches to events, are misp-galaxy:<type>="<value>". MISP links tags to
clusters by Tag.name = GalaxyCluster.tag_name, so the tag_name must be the
actual tag name.

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
"""

from alembic import op

revision = "r1s2t3u4v5w6"
down_revision = "q0r1s2t3u4v5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE galaxy_clusters AS c
        SET tag_name = 'misp-galaxy:' || c.type || '="' || c.value || '"'
        FROM galaxies AS g
        WHERE g.id = c.galaxy_id
          AND c.tag_name = 'misp-galaxy:' || g.type || '=' || c.uuid::text
        """)


def downgrade():
    op.execute("""
        UPDATE galaxy_clusters AS c
        SET tag_name = 'misp-galaxy:' || g.type || '=' || c.uuid::text
        FROM galaxies AS g
        WHERE g.id = c.galaxy_id
          AND c.tag_name = 'misp-galaxy:' || c.type || '="' || c.value || '"'
        """)
