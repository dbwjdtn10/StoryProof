"""
인증 관련 API 엔드포인트
- 회원가입
- 로그인
- 로그아웃
- 토큰 갱신
- 사용자 프로필 조회/수정
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.services.auth_service import AuthService
from backend.core.security import get_current_user_id
from backend.schemas.auth_schema import (
    UserRegister, UserLogin, TokenResponse, UserProfile
)
# User 모델이나 security 유틸리티 직접 import 제거 (Service로 이관됨)

router = APIRouter()

# ===== 회원가입 =====

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    new_user = AuthService.register_user(db, user_data)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "username": new_user.username,
        "mode": new_user.mode,
        "is_active": new_user.is_active,
        "created_at": new_user.created_at
    }


# ===== 로그인 =====

@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    return AuthService.login_user(db, user_data)


# ===== 로그아웃 =====

@router.post("/logout")
async def logout():
    # Service call if needed (e.g., redis blacklist)
    pass


# ===== 토큰 갱신 =====

@router.post("/refresh")
async def refresh_token():
    pass


# ===== 현재 사용자 조회 =====

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """현재 사용자 프로필 조회"""
    return AuthService.get_user_by_id(db, user_id)


# ===== 사용자 프로필 수정 =====

@router.put("/me")
async def update_user_profile():
    pass


# ===== 비밀번호 변경 =====

@router.post("/change-password")
async def change_password():
    pass


# ===== 이메일 인증 =====

@router.post("/verify-email")
async def verify_email():
    pass


# ===== 비밀번호 재설정 요청 =====

@router.post("/forgot-password")
async def forgot_password():
    pass


# ===== 비밀번호 재설정 =====

@router.post("/reset-password")
async def reset_password():
    pass
