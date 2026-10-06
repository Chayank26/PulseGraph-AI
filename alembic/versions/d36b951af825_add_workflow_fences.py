"""Add durable workflow-operation ownership tokens."""
from alembic import op
import sqlalchemy as sa
revision = 'd36b951af825'
down_revision = 'c25a840fe714'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('workflow_operation_fences',
        sa.Column('session_id', sa.String(128), primary_key=True),
        sa.Column('token', sa.String(64), nullable=False))


def downgrade():
    op.drop_table('workflow_operation_fences')
