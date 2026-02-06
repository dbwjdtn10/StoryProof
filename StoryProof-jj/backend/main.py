from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from backend.api.v1.endpoints import auth, novel, chat, analysis
from backend.core.config import settings
from backend.db.session import engine, init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("StoryProof API Server Started")
    init_db()  
    yield
    print("StoryProof API Server Stopped")

app = FastAPI(
    title="StoryProof API",
    description="소설 분석 및 피드백 플랫폼 API",
    version="1.0.0",
    lifespan=lifespan
)

def configure_cors() -> None:
    # 3001 포트를 목록에 추가했습니다.
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],  # 모든 메서드 허용
        allow_headers=["*"],  # 모든 헤더 허용
        max_age=3600,
    )
    print(f"[OK] CORS configured for origins: {origins}")

def register_routers() -> None:
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(novel.router, prefix="/api/v1/novels", tags=["Novel"])
    app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["분석"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
    print("[OK] Routers registered")

# 순서: 라우터 등록 후 CORS 설정 (FastAPI 권장 방식)
register_routers()
configure_cors()

@app.get("/")
async def root():
    return {"message": "StoryProof API", "version": "1.0.0", "status": "running"}

# ⚠️ 기존에 있던 @app.options("/{full_path:path}") 부분은 삭제했습니다.
# CORSMiddleware가 이 역할을 대신 수행하며, 수동 설정 시 충돌이 발생합니다.

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)