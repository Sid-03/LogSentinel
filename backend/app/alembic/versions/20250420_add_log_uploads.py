"""
Add log_uploads table and log_upload_id to log_entries
"""
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = 'add_log_uploads_20250420'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'log_uploads',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('lines_parsed', sa.Integer(), nullable=False),
        sa.Column('lines_failed', sa.Integer(), nullable=False),
    )
    op.add_column('log_entries', sa.Column('log_upload_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('log_uploads.id'), nullable=True))

def downgrade():
    op.drop_column('log_entries', 'log_upload_id')
    op.drop_table('log_uploads')
