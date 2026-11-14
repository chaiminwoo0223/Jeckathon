"""merge cheer record and battle

Revision ID: aecdbc09e983
Revises: 5e308008edb7, 7aa18cb21bf3
Create Date: 2026-11-14 15:49:54.562409

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'aecdbc09e983'
down_revision = ('5e308008edb7', '7aa18cb21bf3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
