"""
데이터베이스 데이터 확인 스크립트
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
print("데이터베이스 테이블별 데이터 개수 확인")
print("=" * 60)

tables = [
    "users",
    "novels", 
    "chapters",
    "analyses",
    "chat_histories",
    "vector_documents"
]

with engine.connect() as conn:
    for table in tables:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"{table:20s}: {count:5d} rows")
    
    print("\n" + "=" * 60)
    print("users 테이블 상세 정보")
    print("=" * 60)
    
    result = conn.execute(text("SELECT id, email, username, created_at FROM users"))
    users = result.fetchall()
    
    if users:
        for user in users:
            print(f"ID: {user[0]}, Email: {user[1]}, Username: {user[2]}, Created: {user[3]}")
    else:
        print("사용자가 없습니다.")
    
    print("\n" + "=" * 60)
    print("novels 테이블 상세 정보")
    print("=" * 60)
    
    result = conn.execute(text("SELECT id, title, author_id, created_at FROM novels"))
    novels = result.fetchall()
    
    if novels:
        for novel in novels:
            print(f"ID: {novel[0]}, Title: {novel[1]}, Author ID: {novel[2]}, Created: {novel[3]}")
    else:
        print("소설이 없습니다.")

print("\n완료!")
