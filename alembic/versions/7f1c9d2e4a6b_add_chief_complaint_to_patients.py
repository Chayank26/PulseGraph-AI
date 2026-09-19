"""add chief complaint to patients

Revision ID: 7f1c9d2e4a6b
Revises: c5a042c433ef
Create Date: 2026-09-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f1c9d2e4a6b"
down_revision: Union[str, Sequence[str], None] = "c5a042c433ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("chief_complaint", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "chief_complaint")
