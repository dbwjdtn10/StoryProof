"""add consistency and prediction to analysistype enum

Revision ID: c3a1f7e82d01
Revises: e15b603034e3
Create Date: 2026-02-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3a1f7e82d01'
down_revision: Union[str, None] = '9f1b46a72e36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL enum은 트랜잭션 밖에서 ADD VALUE 해야 함
    op.execute("ALTER TYPE analysistype ADD VALUE IF NOT EXISTS 'consistency'")
    op.execute("ALTER TYPE analysistype ADD VALUE IF NOT EXISTS 'prediction'")

    # 복합 인덱스: novel_id + chapter_id + analysis_type로 캐시 조회 최적화
    op.create_index(
        'ix_analyses_novel_chapter_type',
        'analyses',
        ['novel_id', 'chapter_id', 'analysis_type'],
    )


def downgrade() -> None:
    op.drop_index('ix_analyses_novel_chapter_type', table_name='analyses')
    # PostgreSQL에서 enum value 제거는 복잡하므로 생략
