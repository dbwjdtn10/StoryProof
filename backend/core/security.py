"""
보안 관련 유틸리티
- JWT 토큰 생성/검증
- 비밀번호 해싱/검증
- 인증 의존성
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models import User
from sqlalchemy.orm import Session


# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer 토큰 스키마
security = HTTPBearer()


# ===== 비밀번호 관련 함수 =====

def hash_password(password: str) -> str:
    """
    비밀번호 해싱
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        str: 해싱된 비밀번호
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해싱된 비밀번호
        
    Returns:
        bool: 비밀번호가 일치하면 True
    """
    return pwd_context.verify(plain_password, hashed_password)


# ===== JWT 토큰 관련 함수 =====

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    액세스 토큰 생성
    
    Args:
        data: 토큰에 포함할 데이터 (user_id, email 등)
        expires_delta: 토큰 만료 시간 (기본값: 30분)
        
    Returns:
        str: JWT 액세스 토큰
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    리프레시 토큰 생성
    
    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 토큰 만료 시간 (기본값: 7일)
        
    Returns:
        str: JWT 리프레시 토큰
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    JWT 토큰 디코딩 및 검증
    
    Args:
        token: JWT 토큰
        
    Returns:
        Dict[str, Any]: 토큰 페이로드
        
    Raises:
        HTTPException: 토큰이 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token(token: str) -> Optional[str]:
    """
    토큰 검증 및 사용자 ID 추출
    
    Args:
        token: JWT 토큰
        
    Returns:
        Optional[str]: 사용자 ID (토큰이 유효하지 않으면 None)
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except HTTPException:
        return None


# ===== 인증 의존성 함수 =====

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    현재 인증된 사용자 ID 반환 (의존성 주입용)
    
    Args:
        credentials: HTTP Bearer 토큰
        
    Returns:
        str: 사용자 ID
        
    Raises:
        HTTPException: 인증 실패 시
    """
    try:
        token = credentials.credentials
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return str(user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    현재 인증된 사용자 객체 반환 (의존성 주입용)
    
    Args:
        user_id: 사용자 ID
        db: 데이터베이스 세션
        
    Returns:
        User: 사용자 객체
        
    Raises:
        HTTPException: 사용자를 찾을 수 없는 경우
    """
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User lookup failed",
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """선택적 인증 (토큰이 없어도 됨)"""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
        db = next(get_db())
        try:
            return db.query(User).filter(User.id == int(user_id)).first()
        finally:
            db.close()
    except Exception:
        return None


# ===== 권한 검증 함수 =====

def require_admin(current_user = Depends(get_current_user)):
    """관리자 권한 필요 (의존성 주입용)"""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_verified_email(current_user = Depends(get_current_user)):
    """이메일 인증 필요 (의존성 주입용)"""
    if not getattr(current_user, "is_email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return current_user
