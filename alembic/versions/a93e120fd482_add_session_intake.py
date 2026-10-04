"""Persist initial clinical intake for deferred workflow execution."""
from alembic import op
import sqlalchemy as sa

revision = "a93e120fd482"
down_revision = "7f1c9d2e4a6b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clinical_sessions", sa.Column("intake_data", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("clinical_sessions", "intake_data")
