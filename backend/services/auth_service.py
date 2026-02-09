from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Dict, Any

from backend.db.models import User
from backend.schemas.auth_schema import UserRegister, UserLogin
from backend.core.security import (
    hash_password, verify_password, 
    create_access_token, create_refresh_token
)
from backend.core.config import settings

class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> User:
        """회원가입 처리"""
        # 이메일 중복 확인
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 사용자명 중복 확인
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # 비밀번호 해싱
        hashed_password = hash_password(user_data.password)
        
        # 사용자 생성
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user

    @staticmethod
    def login_user(db: Session, user_data: UserLogin) -> Dict[str, Any]:
        """로그인 및 토큰 발급"""
        # 1. 이메일로 사용자 조회
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 2. 비밀번호 검증
        if not verify_password(user_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # 3. 토큰 생성
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
