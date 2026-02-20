"""
FastAPI 메인 애플리케이션 진입점
- 앱 초기화 및 설정
- 라우터 등록
- CORS, 미들웨어 설정
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
import os
import threading

# ... (Previous imports)
from backend.api.v1.endpoints import auth, novel, chat, analysis, prediction, character_chat, images
from backend.core.config import settings
from backend.db.session import engine, init_db

# 모델 로딩 상태 플래그 (프론트엔드 폴링용)
_model_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작/종료 시 실행되는 이벤트 핸들러
    """
    # 시작 시 실행할 코드
    print("StoryProof API Server Started")
    
    # Static directory creation
    os.makedirs("backend/static/images", exist_ok=True)
    
    try:
        init_db()  # DB 초기화 (테이블 생성)
        print("[OK] Database initialized successfully")
    except Exception as e:
        print(f"[WARNING] Database initialization failed: {e}")
        print("[INFO] Server starting without database connection")
    
    # 모델 로딩 (백그라운드 스레드에서 실행하여 서버가 먼저 뜨도록 함)
    def _load_models():
        global _model_ready
        import time
        # 서버 시작 안정을 위해 10초 대기 후 모델 로딩
        time.sleep(3)
        try:
            from backend.services.chatbot_service import get_chatbot_service
            get_chatbot_service().warmup()
            _model_ready = True
            print("[OK] All models loaded - server is ready")
        except Exception as e:
            print(f"[Error] Model loading failed: {e}")
            _model_ready = True  # 실패해도 서버는 사용 가능하게
    
    model_thread = threading.Thread(target=_load_models, daemon=True)
    model_thread.start()
    
    yield
    
    # 종료 시 실행할 코드
    print("StoryProof API Server Stopped")


# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="StoryProof API",
    description="소설 분석 및 피드백 플랫폼 API",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="backend/static"), name="static")


def configure_cors() -> None:
    # ... (CORS config)
    """
    CORS 설정 구성
    프론트엔드에서 API 호출을 허용하기 위한 설정
    
    주의: 미들웨어는 역순으로 실행되므로 CORS는 마지막에 추가되어야
    실제로는 먼저 처리됨
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        max_age=3600,
    )
    print(f"[OK] CORS configured for origins: {settings.CORS_ORIGINS}")


def register_routers() -> None:
    """
    API 라우터 등록
    각 엔드포인트 모듈을 앱에 연결
    """
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(novel.router, prefix="/api/v1/novels", tags=["Novel"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["분석"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
    app.include_router(prediction.router, prefix="/api/v1/prediction", tags=["Prediction"])
    app.include_router(character_chat.router, prefix="/api/v1/character-chat", tags=["CharacterChat"])
    app.include_router(images.router, prefix="/api/v1/images", tags=["Images"])
    print("[OK] Routers registered")


# 설정 적용 (순서 중요: CORS를 마지막에 - 역순으로 실행되므로 먼저 처리됨)
register_routers()
configure_cors()


@app.get("/")
async def root():
    """
    루트 엔드포인트 - API 상태 확인
    
    Returns:
        dict: API 상태 정보
    """
    return {
        "message": "StoryProof API",
        "version": "1.0.0",
        "status": "running"
    }


@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    """
    CORS preflight 요청 처리
    브라우저가 실제 요청 전에 OPTIONS 요청을 보낼 때 처리
    """
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    글로벌 예외 핸들러
    모든 처리되지 않은 예외를 캐치
    """
    import logging
    logging.getLogger("storyproof").error(
        f"Unhandled exception [{type(exc).__name__}] on {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/health")
async def health_check():
    """
    헬스 체크 엔드포인트
    서버 상태 및 의존성 연결 상태 확인

    Returns:
        dict: 헬스 체크 결과
    """
    from sqlalchemy import text
    db_status = "disconnected"
    try:
        from backend.db.session import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception:
        pass

    pinecone_status = "disconnected"
    try:
        from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
        engine = EmbeddingSearchEngine()
        if engine.index is not None:
            pinecone_status = "connected"
    except Exception:
        pass

    overall = "healthy" if db_status == "connected" else "degraded"
    return {
        "status": overall,
        "database": db_status,
        "pinecone": pinecone_status,
    }


@app.get("/api/v1/health/ready")
async def readiness_check():
    """
    모델 준비 상태 확인 엔드포인트
    프론트엔드에서 폴링하여 모델 로딩 완료 시점을 파악합니다.
    
    Returns:
        dict: {"ready": bool}
    """
    if _model_ready:
        return {"ready": True}
    else:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "message": "Models are still loading..."}
        )


if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행 (로그 비활성화)
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드에서만 사용
        log_level="info"  # 부팅 로그 확인을 위해 info로 변경
    )
