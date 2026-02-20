"""
인증 관련 API 엔드포인트
====================
- 회원가입
- 로그인
- 로그아웃 / 토큰 갱신 (TODO)
- 현재 사용자 프로필 조회
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.services.auth_service import AuthService
from backend.schemas.auth_schema import (
    UserRegister, UserLogin, TokenResponse, UserProfile
)
from backend.core.security import get_current_user_id

router = APIRouter()


# ===== 회원가입 =====

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """새 사용자 등록"""
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
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """사용자 로그인 및 JWT 토큰 발급"""
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
