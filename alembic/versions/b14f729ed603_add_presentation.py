"""Persist sourced structured triage presentations."""
from alembic import op
import sqlalchemy as sa

revision = 'b14f729ed603'
down_revision = 'a93e120fd482'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cds_results', sa.Column('presentation', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('cds_results', 'presentation')
