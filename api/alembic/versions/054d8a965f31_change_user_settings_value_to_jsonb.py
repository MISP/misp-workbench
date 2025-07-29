"""change user_settings value to jsonb

Revision ID: 054d8a965f31
Revises: 9541c0537355
Create Date: 2025-07-29 12:59:29.973173

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '054d8a965f31'
down_revision = '9541c0537355'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'user_settings',
        'value',
        type_=postgresql.JSONB(),
        postgresql_using='value::jsonb'
    )

    # Ensure that the namespace column is unique
    op.create_unique_constraint('uq_user_settings_namespace', 'user_settings', ['namespace'])


def downgrade():
    op.drop_constraint('uq_user_settings_namespace', 'user_settings', type_='unique')
    op.alter_column(
        'user_settings',
        'value',
        type_=sa.JSON(),
        postgresql_using='value::json'
    )
