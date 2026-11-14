"""add team short_name/color, match venue/round_label

Revision ID: 4c903bf42cf5
Revises: 8aec23f73c6a
Create Date: 2026-11-14 15:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '4c903bf42cf5'
down_revision = '8aec23f73c6a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('team', sa.Column('short_name', sqlmodel.sql.sqltypes.AutoString(length=10), server_default='', nullable=False))
    op.add_column('team', sa.Column('color', sqlmodel.sql.sqltypes.AutoString(length=20), server_default='', nullable=False))
    op.add_column('match', sa.Column('venue', sqlmodel.sql.sqltypes.AutoString(length=50), server_default='', nullable=False))
    op.add_column('match', sa.Column('round_label', sqlmodel.sql.sqltypes.AutoString(length=50), server_default='', nullable=False))


def downgrade():
    op.drop_column('match', 'round_label')
    op.drop_column('match', 'venue')
    op.drop_column('team', 'color')
    op.drop_column('team', 'short_name')
