"""
데이터베이스 세션 관리
- SQLAlchemy 엔진 및 세션 생성
- 의존성 주입을 위한 get_db 함수
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Windows 환경에서 한글 에러 메시지로 인한 UnicodeDecodeError 방지
os.environ["PGCLIENTENCODING"] = "utf-8"

from backend.core.config import settings
from backend.db.models import Base


# ===== 데이터베이스 엔진 생성 =====

def create_db_engine():
    """
    데이터베이스 엔진 생성
    
    Returns:
        Engine: SQLAlchemy 엔진
    """
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )
    return engine


# 엔진 인스턴스 (전역)
engine = create_db_engine()


# ===== 세션 팩토리 생성 =====

def create_session_factory():
    """
    세션 팩토리 생성
    
    Returns:
        sessionmaker: SQLAlchemy 세션 팩토리
    """
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
    return SessionLocal


# 세션 팩토리 인스턴스 (전역)
SessionLocal = create_session_factory()


# ===== 데이터베이스 초기화 =====

def init_db() -> None:
    """
    데이터베이스 초기화
    모든 테이블 생성
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    데이터베이스 삭제
    모든 테이블 삭제 (주의: 개발 환경에서만 사용)
    """
    Base.metadata.drop_all(bind=engine)


def reset_db() -> None:
    """
    데이터베이스 리셋
    모든 테이블 삭제 후 재생성
    """
    drop_db()
    init_db()


# ===== 세션 의존성 =====

def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션 의존성
    FastAPI 엔드포인트에서 사용
    
    Yields:
        Session: SQLAlchemy 세션
        
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== 트랜잭션 헬퍼 =====

class DatabaseTransaction:
    """
    데이터베이스 트랜잭션 컨텍스트 매니저
    
    Example:
        with DatabaseTransaction() as db:
            user = User(email="test@example.com")
            db.add(user)
            # 자동으로 commit 또는 rollback
    """
    
    def __init__(self):
        """트랜잭션 초기화"""
        self.db = SessionLocal()
    
    def __enter__(self) -> Session:
        """
        컨텍스트 진입
        
        Returns:
            Session: 데이터베이스 세션
        """
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        컨텍스트 종료
        
        Args:
            exc_type: 예외 타입
            exc_val: 예외 값
            exc_tb: 예외 트레이스백
        """
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()
        self.db.close()


# ===== 비동기 세션 (선택사항) =====

async def get_async_db():
    """
    비동기 데이터베이스 세션 의존성
    
    Yields:
        AsyncSession: SQLAlchemy 비동기 세션
    """
    # TODO: 비동기 엔진 및 세션 구현
    pass
