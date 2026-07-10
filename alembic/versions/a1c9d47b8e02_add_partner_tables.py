"""add partner (B2B) tables: partners, partner_api_keys, api_usage_logs

Revision ID: a1c9d47b8e02
Revises: f58bd25ccf34
Create Date: 2026-07-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9d47b8e02'
down_revision: Union[str, None] = 'f58bd25ccf34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'partners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='starter'),
        sa.Column('monthly_quota', sa.Integer(), nullable=False, server_default='10000'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('webhook_secret', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_partners_id'), 'partners', ['id'], unique=False)
    op.create_index(op.f('ix_partners_name'), 'partners', ['name'], unique=True)

    op.create_table(
        'partner_api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, server_default='default'),
        sa.Column('key_prefix', sa.String(length=20), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_partner_api_keys_id'), 'partner_api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_partner_api_keys_partner_id'), 'partner_api_keys', ['partner_id'], unique=False)
    op.create_index(op.f('ix_partner_api_keys_key_hash'), 'partner_api_keys', ['key_hash'], unique=True)

    op.create_table(
        'api_usage_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False, server_default='POST'),
        sa.Column('units', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['partner_id'], ['partners.id']),
        sa.ForeignKeyConstraint(['api_key_id'], ['partner_api_keys.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_api_usage_logs_id'), 'api_usage_logs', ['id'], unique=False)
    op.create_index(op.f('ix_api_usage_logs_partner_id'), 'api_usage_logs', ['partner_id'], unique=False)
    op.create_index('ix_usage_partner_created', 'api_usage_logs', ['partner_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_usage_partner_created', table_name='api_usage_logs')
    op.drop_index(op.f('ix_api_usage_logs_partner_id'), table_name='api_usage_logs')
    op.drop_index(op.f('ix_api_usage_logs_id'), table_name='api_usage_logs')
    op.drop_table('api_usage_logs')

    op.drop_index(op.f('ix_partner_api_keys_key_hash'), table_name='partner_api_keys')
    op.drop_index(op.f('ix_partner_api_keys_partner_id'), table_name='partner_api_keys')
    op.drop_index(op.f('ix_partner_api_keys_id'), table_name='partner_api_keys')
    op.drop_table('partner_api_keys')

    op.drop_index(op.f('ix_partners_name'), table_name='partners')
    op.drop_index(op.f('ix_partners_id'), table_name='partners')
    op.drop_table('partners')
