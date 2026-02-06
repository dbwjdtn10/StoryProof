"""
Pinecone 벡터 DB 초기화 스크립트

사용법:
    python scripts/reset_pinecone.py
"""

import sys
import io
from pathlib import Path

# Windows에서 UTF-8 출력 지원
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from backend.core.config import settings

def reset_pinecone():
    """Pinecone 인덱스의 모든 벡터 삭제"""
    try:
        from pinecone import Pinecone
    except ImportError:
        print("❌ Pinecone이 설치되지 않았습니다: pip install pinecone")
        return 1
    
    print("=" * 60)
    print("🗑️  Pinecone 벡터 DB 초기화")
    print("=" * 60)
    
    try:
        # Pinecone 연결
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = settings.PINECONE_INDEX_NAME
        
        print(f"\n📡 Pinecone 인덱스 연결 중: {index_name}")
        
        # 인덱스 확인
        if index_name not in [idx.name for idx in pc.list_indexes()]:
            print(f"❌ 인덱스 '{index_name}'가 존재하지 않습니다.")
            return 1
        
        index = pc.Index(index_name)
        
        # 인덱스 통계 확인
        stats = index.describe_index_stats()
        total_vectors = stats.total_vector_count
        
        print(f"📊 현재 벡터 개수: {total_vectors}")
        
        if total_vectors == 0:
            print("ℹ️  이미 비어있는 인덱스입니다.")
            return 0
        
        # 확인
        confirm = input(f"\n⚠️  경고: {total_vectors}개의 벡터가 모두 삭제됩니다. 계속하시겠습니까? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ 작업이 취소되었습니다.")
            return 0
        
        # 모든 벡터 삭제
        print("\n🗑️  모든 벡터 삭제 중...")
        index.delete(delete_all=True)
        
        print("✅ Pinecone 인덱스가 초기화되었습니다!")
        print("\n다음 단계:")
        print("1. 챕터를 업로드하면 자동으로 벡터화됩니다.")
        print("2. 또는 기존 챕터를 재분석하여 벡터를 다시 생성하세요.")
        
        return 0
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(reset_pinecone())
