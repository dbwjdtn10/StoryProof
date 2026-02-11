"""
기존 챕터의 씬을 Pinecone에 벡터화하는 스크립트

사용법:
    python scripts/vectorize_chapters.py
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

from backend.db.session import SessionLocal
from backend.db.models import VectorDocument, Chapter
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine

def vectorize_existing_chapters():
    """기존 VectorDocument를 Pinecone에 업로드"""
    print("=" * 60)
    print("📤 기존 챕터 벡터화")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # VectorDocument 조회
        vector_docs = db.query(VectorDocument).all()
        
        if not vector_docs:
            print("ℹ️  벡터화할 문서가 없습니다.")
            return 0
        
        print(f"\n📊 총 {len(vector_docs)}개의 문서를 벡터화합니다.")
        
        # novel_id별로 그룹화
        docs_by_novel = {}
        for doc in vector_docs:
            if doc.novel_id not in docs_by_novel:
                docs_by_novel[doc.novel_id] = []
            docs_by_novel[doc.novel_id].append(doc.metadata_json)
        
        # 각 novel별로 벡터화
        search_engine = EmbeddingSearchEngine()
        
        for novel_id, documents in docs_by_novel.items():
            print(f"\n📖 Novel {novel_id}: {len(documents)}개 문서 처리 중...")
            search_engine.add_documents(documents, novel_id)
        
        print("\n✅ 모든 문서가 Pinecone에 업로드되었습니다!")
        return 0
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(vectorize_existing_chapters())
