"""Add deployment_region/dedicated_instance_url to partners

Revision ID: 7f4d9a2e6c31
Revises: c5a08e3f1b92
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f4d9a2e6c31'
down_revision: Union[str, None] = 'c5a08e3f1b92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('partners', sa.Column(
        'deployment_region', sa.String(length=50), nullable=False, server_default='shared'
    ))
    op.add_column('partners', sa.Column('dedicated_instance_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('partners', 'dedicated_instance_url')
    op.drop_column('partners', 'deployment_region')
