"""ensure log_uploads table

Revision ID: 364203f16dcc
Revises: ba5371049841
Create Date: 2025-04-20 15:00:38.529590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '364203f16dcc'
down_revision: Union[str, None] = 'ba5371049841'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('log_uploads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('filename', sa.String(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    sa.Column('lines_parsed', sa.Integer(), nullable=False),
    sa.Column('lines_failed', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id')
    )
    op.add_column('log_entries', sa.Column('log_upload_id', sa.UUID(), nullable=True))
    op.create_unique_constraint(None, 'log_entries', ['id'])
    op.create_foreign_key(None, 'log_entries', 'log_uploads', ['log_upload_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'log_entries', type_='foreignkey')
    op.drop_constraint(None, 'log_entries', type_='unique')
    op.drop_column('log_entries', 'log_upload_id')
    op.drop_table('log_uploads')
    # ### end Alembic commands ###
