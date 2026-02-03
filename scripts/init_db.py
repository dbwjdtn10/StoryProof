"""
데이터베이스 초기화 스크립트

사용법:
    # 데이터베이스 초기화 (테이블 생성)
    python scripts/init_db.py

    # 데이터베이스 완전 리셋 (모든 테이블 삭제 후 재생성)
    python scripts/init_db.py --reset

    # 초기 데이터 생성 포함
    python scripts/init_db.py --with-seed-data
"""

import sys
import os
from pathlib import Path

# Windows에서 UTF-8 출력 지원
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(project_root / ".env")

from backend.core.config import settings
from backend.db.models import Base, User
from backend.core.security import hash_password


def drop_all_tables(engine):
    """모든 테이블 삭제"""
    print("🗑️  모든 테이블을 삭제합니다...")
    
    # Alembic 버전 테이블도 삭제
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE;"))
        conn.commit()
    
    # 모든 모델 테이블 삭제
    Base.metadata.drop_all(bind=engine)
    print("✅ 모든 테이블이 삭제되었습니다.")


def create_all_tables(engine):
    """모든 테이블 생성"""
    print("📦 데이터베이스 테이블을 생성합니다...")
    Base.metadata.create_all(bind=engine)
    print("✅ 모든 테이블이 생성되었습니다.")


def check_tables(engine):
    """생성된 테이블 확인"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print(f"\n📋 생성된 테이블 목록 ({len(tables)}개):")
    for table in sorted(tables):
        print(f"   - {table}")
    
    return tables


def create_seed_data(engine):
    """초기 데이터 생성 (선택적)"""
    print("\n🌱 초기 데이터를 생성합니다...")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 테스트 사용자 생성
        test_user = User(
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("testpassword123"),
            is_active=True,
            is_verified=True
        )
        
        # 이미 존재하는지 확인
        existing_user = session.query(User).filter_by(email="test@example.com").first()
        if not existing_user:
            session.add(test_user)
            session.commit()
            print("✅ 테스트 사용자 생성 완료 (email: test@example.com, password: testpassword123)")
        else:
            print("ℹ️  테스트 사용자가 이미 존재합니다.")
            
    except Exception as e:
        session.rollback()
        print(f"❌ 초기 데이터 생성 실패: {e}")
    finally:
        session.close()


def init_alembic_version(engine):
    """Alembic 버전 테이블 초기화"""
    print("\n🔧 Alembic 마이그레이션 설정...")
    print("   다음 명령어를 실행하세요:")
    print("   alembic stamp head")


def main():
    parser = argparse.ArgumentParser(description="데이터베이스 초기화 스크립트")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="모든 테이블을 삭제하고 재생성합니다 (주의: 모든 데이터가 삭제됩니다!)"
    )
    parser.add_argument(
        "--with-seed-data",
        action="store_true",
        help="초기 테스트 데이터를 생성합니다"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 StoryProof 데이터베이스 초기화")
    print("=" * 60)
    
    # 데이터베이스 연결
    try:
        print(f"\n📡 데이터베이스 연결 중...")
        print(f"   URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
        engine = create_engine(settings.DATABASE_URL)
        
        # 연결 테스트
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ 데이터베이스 연결 성공!")
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        print("\n💡 해결 방법:")
        print("   1. PostgreSQL이 실행 중인지 확인하세요")
        print("   2. .env 파일의 DATABASE_URL이 올바른지 확인하세요")
        print("   3. 데이터베이스가 생성되어 있는지 확인하세요")
        return 1
    
    # 리셋 모드
    if args.reset:
        confirm = input("\n⚠️  경고: 모든 데이터가 삭제됩니다. 계속하시겠습니까? (yes/no): ")
        if confirm.lower() != "yes":
            print("❌ 작업이 취소되었습니다.")
            return 0
        
        drop_all_tables(engine)
    
    # 테이블 생성
    create_all_tables(engine)
    
    # 생성된 테이블 확인
    tables = check_tables(engine)
    
    # 초기 데이터 생성
    if args.with_seed_data:
        create_seed_data(engine)
    
    # Alembic 설정 안내
    init_alembic_version(engine)
    
    print("\n" + "=" * 60)
    print("✅ 데이터베이스 초기화 완료!")
    print("=" * 60)
    print("\n다음 단계:")
    print("1. alembic stamp head  # Alembic 마이그레이션 히스토리 초기화")
    print("2. uvicorn backend.main:app --reload  # 백엔드 서버 실행")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
