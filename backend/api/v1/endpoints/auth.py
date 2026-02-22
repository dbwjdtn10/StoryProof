"""
인증 관련 API 엔드포인트
====================
- 회원가입
- 로그인
- 로그아웃 / 토큰 갱신 (TODO)
- 현재 사용자 프로필 조회
"""

import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.services.auth_service import AuthService
from backend.schemas.auth_schema import (
    UserRegister, UserLogin, TokenResponse, UserProfile
)
from backend.core.security import get_current_user_id

router = APIRouter()


# ===== Rate Limiter (IP 기반, 의존성 없음) =====

_rate_store: dict = defaultdict(list)  # IP → [timestamps]
_RATE_LIMIT = 10  # 최대 요청 수
_RATE_WINDOW = 60  # 윈도우 (초)


def _check_rate_limit(request: Request):
    """IP 기반 rate limiting — 분당 10회 초과 시 429 반환"""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    # 윈도우 외 기록 제거
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
        )
    _rate_store[ip].append(now)

    # 메모리 누수 방지: 오래된 항목 정리
    if len(_rate_store) > 10000:
        expired_ips = [k for k, v in _rate_store.items() if not v or now - v[-1] >= _RATE_WINDOW]
        for k in expired_ips:
            del _rate_store[k]


# ===== 회원가입 =====

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """새 사용자 등록"""
    _check_rate_limit(request)
    new_user = AuthService.register_user(db, user_data)

    return {
        "id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        "user_mode": new_user.user_mode,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at
    }


# ===== 로그인 =====

@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """사용자 로그인 및 JWT 토큰 발급"""
    _check_rate_limit(request)
    return AuthService.login_user(db, user_data)


# ===== 로그아웃 =====

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    """로그아웃 처리 (클라이언트 토큰 삭제로 처리, TODO: Redis 블랙리스트 구현)"""
    return None


# ===== 토큰 갱신 =====

@router.post("/refresh", response_model=None)
def refresh_token():
    """JWT 토큰 갱신 - 미구현 (클라이언트에서 재로그인 유도)"""
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="토큰 갱신은 지원되지 않습니다. 다시 로그인해주세요.")


# ===== 현재 사용자 조회 =====

@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """현재 사용자 프로필 조회"""
    return AuthService.get_user_by_id(db, user_id)
