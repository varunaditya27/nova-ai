"""baseline schema — full current model set via create_all

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-05
"""
from alembic import op

from infra.db.base import Base
import infra.db.models  # noqa: F401 — register every table

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(op.get_bind())
