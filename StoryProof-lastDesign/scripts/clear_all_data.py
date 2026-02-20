"""
데이터베이스의 모든 데이터를 삭제하고 테이블 구조만 남기는 스크립트
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 데이터베이스 URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 엔진 생성
engine = create_engine(DATABASE_URL)

print("=" * 60)
print("WARNING: 데이터베이스 데이터 삭제 시작")
print("=" * 60)

# 삭제할 테이블 목록 (외래키 관계 역순으로 삭제)
tables_to_clear = [
    "chat_histories",      # User 참조
    "vector_documents",    # Novel, Chapter 참조
    "analyses",            # Novel, Chapter 참조
    "chapters",            # Novel 참조
    "novels",              # User 참조
    "users"                # 최상위
]

with engine.connect() as conn:
    # 트랜잭션 시작
    trans = conn.begin()
    
    try:
        for table in tables_to_clear:
            # 삭제 전 개수 확인
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count_before = result.scalar()
            
            # 데이터 삭제 (TRUNCATE는 외래키 때문에 DELETE 사용)
            conn.execute(text(f"DELETE FROM {table}"))
            
            # 삭제 후 개수 확인
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count_after = result.scalar()
            
            print(f"[OK] {table:20s}: {count_before:5d} rows -> {count_after:5d} rows")
        
        # 시퀀스 리셋 (ID를 1부터 다시 시작)
        print("\n" + "=" * 60)
        print("ID 시퀀스 리셋 중...")
        print("=" * 60)
        
        sequences = [
            "users_id_seq",
            "novels_id_seq",
            "chapters_id_seq",
            "analyses_id_seq",
            "chat_histories_id_seq",
            "vector_documents_id_seq"
        ]
        
        for seq in sequences:
            try:
                conn.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                print(f"[OK] {seq} 리셋 완료")
            except Exception as e:
                print(f"[WARN] {seq} 리셋 실패 (시퀀스가 없을 수 있음): {e}")
        
        # 커밋
        trans.commit()
        
        print("\n" + "=" * 60)
        print("SUCCESS: 모든 데이터 삭제 완료!")
        print("=" * 60)
        
    except Exception as e:
        # 롤백
        trans.rollback()
        print(f"\nERROR: 오류 발생: {e}")
        print("모든 변경사항이 롤백되었습니다.")
        raise

print("\n최종 확인:")
print("=" * 60)

with engine.connect() as conn:
    for table in tables_to_clear:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"{table:20s}: {count:5d} rows")

print("\n완료! 테이블 구조는 유지되고 모든 데이터가 삭제되었습니다.")
