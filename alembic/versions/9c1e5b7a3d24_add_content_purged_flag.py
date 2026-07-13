"""Add content_purged flag to chapters (fix reanalyze-after-purge bug)

Revision ID: 9c1e5b7a3d24
Revises: 7f4d9a2e6c31
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1e5b7a3d24'
down_revision: Union[str, None] = '7f4d9a2e6c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chapters', sa.Column(
        'content_purged', sa.Boolean(), nullable=False, server_default=sa.false()
    ))


def downgrade() -> None:
    op.drop_column('chapters', 'content_purged')
