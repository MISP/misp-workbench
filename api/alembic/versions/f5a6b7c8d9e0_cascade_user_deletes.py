"""let users (and tags) be deleted

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-11-18 21:00:00.000000

Deleting a user failed with a ForeignKeyViolation as soon as they had
created a tag, a setting, an API key or a notification, because those
foreign keys had no ON DELETE rule. A user's own rows (settings,
notifications, API keys, hunts) now go with them. A tag is shared
vocabulary that other people's events and feeds use, so it outlives the
user who created it, and so does a sharing group that merely names them as
its sync user: both just have the column cleared.

Deleting a tag hit the same wall, so the rows that point at one follow the
same idea: link rows go with it, and a feed that tags what it ingests
simply stops doing so.

Existing installations do not all carry the same constraints (some are
missing, some already cascade), so each one is looked up rather than
assumed by name, and a table that does not exist is skipped.

"""

import sqlalchemy as sa
from alembic import op

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None

# (table, column, referenced table, ON DELETE rule)
_FOREIGN_KEYS = [
    ("tags", "user_id", "users", "SET NULL"),
    ("user_settings", "user_id", "users", "CASCADE"),
    ("notifications", "user_id", "users", "CASCADE"),
    ("api_keys", "user_id", "users", "CASCADE"),
    ("hunts", "user_id", "users", "CASCADE"),
    ("object_templates", "user_id", "users", "CASCADE"),
    ("sharing_groups", "sync_user_id", "users", "SET NULL"),
    ("event_tags", "tag_id", "tags", "CASCADE"),
    ("attribute_tags", "tag_id", "tags", "CASCADE"),
    ("galaxy_cluster_relation_tags", "tag_id", "tags", "CASCADE"),
    ("feeds", "tag_id", "tags", "SET NULL"),
]

# Already cascading in the models before this revision; downgrade keeps them.
_KEEP_ON_DOWNGRADE = {("api_keys", "user_id"), ("hunts", "user_id")}


def _replace_fk(table, column, referred, ondelete):
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return
    if column not in {c["name"] for c in inspector.get_columns(table)}:
        return
    for fk in inspector.get_foreign_keys(table):
        if fk["constrained_columns"] == [column] and fk["referred_table"] == referred:
            op.drop_constraint(fk["name"], table, type_="foreignkey")
    op.create_foreign_key(
        f"{table}_{column}_fkey",
        table,
        referred,
        [column],
        ["id"],
        ondelete=ondelete,
    )


def upgrade():
    for table, column, referred, ondelete in _FOREIGN_KEYS:
        _replace_fk(table, column, referred, ondelete)


def downgrade():
    for table, column, referred, _ in reversed(_FOREIGN_KEYS):
        if (table, column) in _KEEP_ON_DOWNGRADE:
            continue
        _replace_fk(table, column, referred, None)
