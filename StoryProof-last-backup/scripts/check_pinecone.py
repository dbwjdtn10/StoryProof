import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.config import settings
from sqlalchemy import text
from backend.db.session import engine

def diagnose_pinecone():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    index_name = os.getenv("PINECONE_INDEX_NAME")
    
    print("🔍 [1/2] Database 진단 시작...")
    if db_url and '@' in db_url:
        print(f"   DATABASE_URL: {db_url.split('@')[1]}")
    else:
        print(f"   DATABASE_URL: {db_url}")
    
    # 1. Database 연결 테스트
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database 연결 성공!")
        
        # 테이블 확인
        from backend.db.models import User
        with engine.connect() as db_conn:
            try:
                count = db_conn.execute(text("SELECT count(*) FROM users")).scalar()
                print(f"✅ Users 테이블 확인됨 (총 {count}명)")
            except Exception as e:
                print(f"❌ Users 테이블 조회 실패 (테이블이 없을 수 있습니다): {e}")
    except Exception as e:
        try:
            errmsg = str(e)
            print(f"❌ Database 연결 실패: {errmsg}")
        except UnicodeDecodeError:
            print("❌ Database 연결 실패! (인코딩 오류 발생 - 보통 비밀번호가 틀렸을 때 나타납니다.)")
            print("💡 해결 방법: .env의 비밀번호에 특수문자가 있다면 pgAdmin에서 간단한 비밀번호로 변경해 보세요.")

    # 2. Pinecone 진단
    print("\n🔍 [2/2] Pinecone 진단 시작...")
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ PINECONE_API_KEY가 설정되지 않았습니다.")
        return

    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        
        print("1. 연결 테스트 중...")
        indexes = pc.list_indexes()
        index_names = [idx.name for idx in indexes]
        print(f"✅ 연결 성공! 프로젝트 내 인덱스 목록: {index_names}")
        
        if index_name not in index_names:
            print(f"\n❌ 중요: '.env'에 설정된 '{index_name}' 인덱스가 존재하지 않습니다.")
            print(f"💡 해결 방법: Pinecone 대시보드(app.pinecone.io)에서 '{index_name}' 인덱스를 생성하세요.")
            print("   - Dimension: 384")
            print("   - Metric: Cosine")
        else:
            print(f"✅ '{index_name}' 인덱스가 확인되었습니다.")
            
    except Exception as e:
        print(f"\n❌ Pinecone 연결 시도 중 오류 발생: {e}")
        if "renamed" in str(e).lower():
            print("💡 해결 방법: 'pip uninstall pinecone-client pinecone' 후 'pip install pinecone' 실행")

if __name__ == "__main__":
    diagnose_pinecone()
