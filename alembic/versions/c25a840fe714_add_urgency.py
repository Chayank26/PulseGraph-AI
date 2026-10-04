"""Persist the latest urgency screen."""
from alembic import op
import sqlalchemy as sa
revision = 'c25a840fe714'
down_revision = 'b14f729ed603'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('cds_results', sa.Column('urgency', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('cds_results', 'urgency')
