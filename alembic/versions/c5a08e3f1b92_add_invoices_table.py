"""Add invoices table for monthly billing automation

Revision ID: c5a08e3f1b92
Revises: e7b2c19f4a08
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5a08e3f1b92'
down_revision: Union[str, None] = 'e7b2c19f4a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('partner_id', sa.Integer(), sa.ForeignKey('partners.id'), nullable=False, index=True),
        sa.Column('period_year', sa.Integer(), nullable=False),
        sa.Column('period_month', sa.Integer(), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False),
        sa.Column('total_units', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('included_units', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_units', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('base_fee_krw', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_unit_price_krw', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('overage_amount_krw', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_amount_krw', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index(
        'ix_invoice_partner_period', 'invoices',
        ['partner_id', 'period_year', 'period_month'], unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_invoice_partner_period', table_name='invoices')
    op.drop_table('invoices')
