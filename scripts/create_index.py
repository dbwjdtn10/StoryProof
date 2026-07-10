"""
Pinecone 인덱스 생성 스크립트 (최초 1회)
========================================
.env의 PINECONE_API_KEY 계정에 벡터 인덱스를 생성한다.
이미 존재하면 아무것도 하지 않는다 (재실행 안전).

사용법: python scripts/create_index.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.config import settings

# 임베딩 모델(multilingual-e5-small)의 벡터 차원
DIMENSION = 384
METRIC = "cosine"


def main():
    if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY.startswith("your-"):
        print("[ERROR] .env에 PINECONE_API_KEY를 먼저 설정하세요.")
        sys.exit(1)

    try:
        from pinecone import Pinecone, ServerlessSpec
    except ImportError:
        print("[ERROR] pinecone 패키지가 없습니다: pip install pinecone-client")
        sys.exit(1)

    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index_name = settings.PINECONE_INDEX_NAME

    try:
        existing = [idx.name for idx in pc.list_indexes()]
    except AttributeError:
        existing = pc.list_indexes()

    if index_name in existing:
        print(f"[OK] 인덱스 '{index_name}' 이미 존재 — 생성 불필요")
        stats = pc.Index(index_name).describe_index_stats()
        print(f"     저장된 벡터 수: {stats.get('total_vector_count', 0)}")
        return

    print(f"[..] 인덱스 '{index_name}' 생성 중 (dim={DIMENSION}, metric={METRIC})...")
    pc.create_index(
        name=index_name,
        dimension=DIMENSION,
        metric=METRIC,
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),  # 무료 티어 지원 리전
    )
    print(f"[OK] 인덱스 '{index_name}' 생성 완료")


if __name__ == "__main__":
    main()
