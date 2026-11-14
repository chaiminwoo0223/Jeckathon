"""merge battle and cheer record

Revision ID: 8aec23f73c6a
Revises: 5e308008edb7, 7aa18cb21bf3
Create Date: 2026-11-14 15:49:27.286840

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "8aec23f73c6a"
down_revision = ("5e308008edb7", "7aa18cb21bf3")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
