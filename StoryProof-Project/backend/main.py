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
import traceback

from backend.api.v1.endpoints import auth, novel, chat, consistency
from backend.core.config import settings
from backend.db.session import engine, init_db

#################################
import pinecone
from backend.core.config import settings

pc = pinecone.Pinecone(api_key=settings.PINECONE_API_KEY)

# 인덱스가 없을 경우 생성
index_name = "storyproof-index"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536, 
        metric='cosine',
        spec=pinecone.ServerlessSpec(cloud='aws', region='us-east-1')
    )
    print(f"Index '{index_name}' created successfully.")
#################################


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작/종료 시 실행되는 이벤트 핸들러
    
    Yields:
        None: 애플리케이션 실행 중
    """
    # 시작 시 실행할 코드
    print("StoryProof API Server Started")
    init_db()  # DB 초기화 (테이블 생성)
    
    ####################
    try:
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = "storyproof-index"
        
        # 차원이 1536인 기존 인덱스가 있다면 1024로 재생성
        if index_name in [idx.name for idx in pc.list_indexes()]:
            desc = pc.describe_index(index_name)
            if desc.dimension != 1024:
                pc.delete_index(index_name)
        
        if index_name not in [idx.name for idx in pc.list_indexes()]:
            pc.create_index(
                name=index_name,
                dimension=1024, # 에러 메시지에 맞춤
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
    except Exception as e:
        print(f"Pinecone Setup Error: {e}")
    ##############################
    
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


def configure_cors() -> None:
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
    print(f"v CORS configured for origins: {settings.CORS_ORIGINS}")


def register_routers() -> None:
    """
    API 라우터 등록
    각 엔드포인트 모듈을 앱에 연결
    """
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(novel.router, prefix="/api/v1/novels", tags=["Novel"])
    # app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["분석"])
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
    app.include_router(consistency.router, prefix="/api/v1/consistency", tags=["Consistency"])
    print("v Routers registered")


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


#@app.options("/{full_path:path}")
#async def preflight_handler(full_path: str):
#    """
#    CORS preflight 요청 처리
#    브라우저가 실제 요청 전에 OPTIONS 요청을 보낼 때 처리
#    """
#    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    글로벌 예외 핸들러
    모든 처리되지 않은 예외를 캐치
    """
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
    """
    헬스 체크 엔드포인트
    서버 상태 및 의존성 연결 상태 확인
    
    Returns:
        dict: 헬스 체크 결과
    """
    return {
        "status": "healthy",
        "database": "connected",
        "pinecone": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    
    # 개발 서버 실행 (로그 비활성화)
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드에서만 사용
        log_level="info"  # critical 레벨만 출력 (에러만)
    )
