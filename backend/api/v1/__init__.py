"""
API v1 라우터 초기화
모든 엔드포인트 라우터를 통합
"""

from fastapi import APIRouter
from backend.api.v1.endpoints import auth, novel, analysis, chat, prediction, character_chat, images

# API v1 라우터 생성
api_router = APIRouter()

# 각 엔드포인트 라우터 등록
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(novel.router, prefix="/novels", tags=["novels"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(prediction.router, prefix="/prediction", tags=["prediction"])
api_router.include_router(character_chat.router, prefix="/character-chat", tags=["character-chat"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
