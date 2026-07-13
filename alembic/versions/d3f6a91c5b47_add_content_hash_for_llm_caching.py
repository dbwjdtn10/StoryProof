"""Add content_hash columns for LLM result caching

Revision ID: d3f6a91c5b47
Revises: a1c9d47b8e02
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f6a91c5b47'
down_revision: Union[str, None] = 'a1c9d47b8e02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chapters', sa.Column('storyboard_content_hash', sa.String(length=64), nullable=True))
    op.add_column('analyses', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_analyses_content_hash', 'analyses', ['content_hash'])


def downgrade() -> None:
    op.drop_index('ix_analyses_content_hash', table_name='analyses')
    op.drop_column('analyses', 'content_hash')
    op.drop_column('chapters', 'storyboard_content_hash')
