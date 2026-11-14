"""merge settlement and kbo schedule

Revision ID: 9dfea1b86d77
Revises: 4c903bf42cf5, 605c475e3a37
Create Date: 2026-11-14 15:58:23.242870

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '9dfea1b86d77'
down_revision = ('4c903bf42cf5', '605c475e3a37')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
