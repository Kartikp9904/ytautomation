"""add_advanced_upload_options

Revision ID: 2b73ef8fd2e4
Revises: 1a42ef3fd1d3
Create Date: 2026-08-18 12:28:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b73ef8fd2e4'
down_revision: Union[str, None] = '1a42ef3fd1d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('made_for_kids', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('age_restricted', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('default_language', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('default_audio_language', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('contains_synthetic_media', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('preset_category', sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('schedules', schema=None) as batch_op:
        batch_op.drop_column('preset_category')
        batch_op.drop_column('contains_synthetic_media')
        batch_op.drop_column('default_audio_language')
        batch_op.drop_column('default_language')
        batch_op.drop_column('age_restricted')
        batch_op.drop_column('made_for_kids')
