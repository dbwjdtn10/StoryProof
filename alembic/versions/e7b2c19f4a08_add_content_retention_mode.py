"""Add content_retention_mode to partners

Revision ID: e7b2c19f4a08
Revises: d3f6a91c5b47
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7b2c19f4a08'
down_revision: Union[str, None] = 'd3f6a91c5b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('partners', sa.Column(
        'content_retention_mode', sa.String(length=20), nullable=False, server_default='full'
    ))


def downgrade() -> None:
    op.drop_column('partners', 'content_retention_mode')
