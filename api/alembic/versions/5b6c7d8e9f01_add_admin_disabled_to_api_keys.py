"""add admin_disabled to api_keys

Independent admin-controlled hold so that an admin's incident-response
disable cannot be undone by the key's owner. Authentication denies when
either `disabled` (owner) or `admin_disabled` (admin) is true.

Revision ID: 5b6c7d8e9f01
Revises: 4a5b6c7d8e9f
Create Date: 2026-04-22 11:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5b6c7d8e9f01"
down_revision = "4a5b6c7d8e9f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "api_keys",
        sa.Column(
            "admin_disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("api_keys", "admin_disabled")
