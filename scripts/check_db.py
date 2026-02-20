"""
데이터베이스 상태 확인 스크립트

사용법:
    python scripts/check_db.py
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

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(project_root / ".env")

from backend.core.config import settings
from backend.db.models import Base


def check_connection(engine):
    """데이터베이스 연결 확인"""
    print("📡 데이터베이스 연결 테스트...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ 연결 성공!")
            print(f"   PostgreSQL 버전: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False


def check_database_exists(engine):
    """데이터베이스 존재 확인"""
    print("\n📦 데이터베이스 확인...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"✅ 현재 데이터베이스: {db_name}")
            return True
    except Exception as e:
        print(f"❌ 데이터베이스 확인 실패: {e}")
        return False


def check_tables(engine):
    """테이블 존재 확인"""
    print("\n📋 테이블 확인...")
    
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    # 필요한 테이블 목록 (models.py에서 정의된 테이블)
    required_tables = {
        'users',
        'novels',
        'chapters',
        'analyses',
        'chat_histories',
        'vector_documents'
    }
    
    print(f"   필요한 테이블: {len(required_tables)}개")
    print(f"   존재하는 테이블: {len(existing_tables)}개")
    
    # 존재하는 테이블
    if existing_tables:
        print("\n   ✅ 존재하는 테이블:")
        for table in sorted(existing_tables):
            if table in required_tables:
                print(f"      ✓ {table}")
            else:
                print(f"      ? {table} (추가 테이블)")
    
    # 누락된 테이블
    missing_tables = required_tables - existing_tables
    if missing_tables:
        print("\n   ❌ 누락된 테이블:")
        for table in sorted(missing_tables):
            print(f"      ✗ {table}")
        return False
    
    print("\n✅ 모든 필수 테이블이 존재합니다!")
    return True


def check_alembic_version(engine):
    """Alembic 마이그레이션 버전 확인"""
    print("\n🔧 Alembic 마이그레이션 상태...")
    
    try:
        with engine.connect() as conn:
            # alembic_version 테이블 확인
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version');"
            ))
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("   ⚠️  alembic_version 테이블이 없습니다.")
                print("   💡 다음 명령어를 실행하세요:")
                print("      alembic stamp head")
                return False
            
            # 현재 버전 확인
            result = conn.execute(text("SELECT version_num FROM alembic_version;"))
            row = result.fetchone()
            
            if row:
                version = row[0]
                print(f"   ✅ 현재 마이그레이션 버전: {version}")
                return True
            else:
                print("   ⚠️  마이그레이션 버전이 설정되지 않았습니다.")
                print("   💡 다음 명령어를 실행하세요:")
                print("      alembic upgrade head")
                return False
                
    except Exception as e:
        print(f"   ❌ 확인 실패: {e}")
        return False


def check_table_schema(engine):
    """테이블 스키마 확인 (샘플)"""
    print("\n🔍 테이블 스키마 확인 (users 테이블)...")
    
    inspector = inspect(engine)
    
    if 'users' not in inspector.get_table_names():
        print("   ⚠️  users 테이블이 없습니다.")
        return False
    
    columns = inspector.get_columns('users')
    print(f"   컬럼 수: {len(columns)}개")
    
    expected_columns = {
        'id', 'email', 'username', 'hashed_password',
        'is_active', 'is_verified', 'is_admin',
        'created_at', 'updated_at', 'last_login'
    }
    
    actual_columns = {col['name'] for col in columns}
    
    missing_columns = expected_columns - actual_columns
    if missing_columns:
        print(f"   ❌ 누락된 컬럼: {missing_columns}")
        return False
    
    print("   ✅ 스키마가 올바릅니다!")
    return True


def main():
    print("=" * 60)
    print("🔍 StoryProof 데이터베이스 상태 확인")
    print("=" * 60)
    
    # 데이터베이스 URL 표시 (비밀번호 숨김)
    db_url = settings.DATABASE_URL
    if '@' in db_url:
        safe_url = db_url.split('@')[1]
    else:
        safe_url = db_url
    print(f"\n데이터베이스: {safe_url}")
    
    # 연결 생성
    try:
        engine = create_engine(settings.DATABASE_URL)
    except Exception as e:
        print(f"❌ 엔진 생성 실패: {e}")
        return 1
    
    # 각종 확인 수행
    checks = [
        ("연결", check_connection(engine)),
        ("데이터베이스", check_database_exists(engine)),
        ("테이블", check_tables(engine)),
        ("스키마", check_table_schema(engine)),
        ("마이그레이션", check_alembic_version(engine)),
    ]
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 검사 결과 요약")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{check_name:15s}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("✅ 모든 검사를 통과했습니다!")
        print("\n다음 단계:")
        print("   uvicorn backend.main:app --reload")
        return 0
    else:
        print("⚠️  일부 검사에 실패했습니다.")
        print("\n💡 해결 방법:")
        print("   1. 테이블이 없는 경우:")
        print("      python scripts/init_db.py")
        print("      alembic stamp head")
        print("\n   2. 스키마가 맞지 않는 경우:")
        print("      python scripts/init_db.py --reset")
        print("      alembic stamp head")
        print("\n   3. 마이그레이션 문제:")
        print("      alembic upgrade head")
        return 1


if __name__ == "__main__":
    sys.exit(main())
