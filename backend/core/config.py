"""
애플리케이션 설정 관리
- 환경 변수 로드
- 데이터베이스, Redis, API 키 설정
- 개발/프로덕션 환경 분리
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    애플리케이션 전역 설정
    환경 변수에서 자동으로 값을 로드
    """
    
    # ===== 기본 설정 =====
    APP_NAME: str = "StoryProof"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"  # development, production, staging
    
    # ===== 서버 설정 =====
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ===== 데이터베이스 설정 =====
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/storyproof"
    DB_ECHO: bool = False  # SQLAlchemy 쿼리 로깅
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    
    # ===== Redis 설정 =====
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # ===== JWT 인증 설정 =====
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ===== CORS 설정 =====
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]
    
    # ===== AI 모델 설정 =====
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 2000
    
    # ===== Google Gemini 설정 =====
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_STRUCTURING_MODEL: str = "gemini-2.5-flash"  # 앵커 찾기 등 구조화용
    GEMINI_CHAT_MODEL: str = "gemini-2.5-flash"  # 챗봇용
    GEMINI_REFINE_MODEL: str = "gemini-2.0-flash"  # 이미지 프롬프트 정제용
    IMAGEN_GENERATE_MODEL: str = "imagen-4.0-generate-001"  # 이미지 생성용
    
    # ===== LangChain 설정 =====
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_TRACING: bool = False
    
    # ===== ChromaDB 설정 =====
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "storyproof_novels"
    
    # ===== Pinecone 설정 =====
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENV: str = "your-pinecone-environment"
    PINECONE_INDEX_NAME: str = "story-child-index-384" # Single index for both 384d models
    
    # ===== Embedding Models =====
    KOREAN_EMBEDDING_MODEL: str = "dragonkue/multilingual-e5-small-ko"
    MULTILINGUAL_EMBEDDING_MODEL: str = "intfloat/multilingual-e5-small"
    ENABLE_RERANKER: bool = False  # 기본값 False (메모리 절약), True로 설정 시 Reranker 활성화
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # ===== 검색 설정 =====
    SEARCH_DEFAULT_ALPHA: float = 0.7            # Vector 70%, BM25 30% (한국어 키워드 매칭 강화)
    SEARCH_DEFAULT_SIMILARITY_THRESHOLD: float = 0.2  # Reranker 도입으로 기준 하향
    SEARCH_DEFAULT_TOP_K: int = 8                # 검색 후보 수 (더 많은 컨텍스트)
    SEARCH_CONTEXT_MAX_CHARS: int = 5000         # Gemini 컨텍스트 최대 길이
    GEMINI_RESPONSE_TEMPERATURE: float = 0.1
    GEMINI_RESPONSE_TOP_P: float = 0.8
    GEMINI_RESPONSE_TOP_K: int = 20
    ITERATIVE_RETRIEVAL_THRESHOLD: float = 0.79  # best_similarity < 이 값이면 쿼리 재구성 후 재검색 (E5 모델 유사도 분포: 0.7~0.9)
    
    # ===== Chunking Strategy =====
    CHILD_CHUNK_SIZE: int = 500  # 200 -> 500 (문맥 확보)
    CHILD_CHUNK_OVERLAP: int = 100  # 50 -> 100 (연결성 강화)
    
    # ===== Celery 설정 =====
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # ===== 파일 업로드 설정 =====
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list[str] = [".txt", ".docx", ".pdf"]
    
    # ===== 로깅 설정 =====
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    class Config:
        """Pydantic 설정"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    @property
    def database_url_async(self) -> str:
        """
        비동기 데이터베이스 URL 반환
        
        Returns:
            str: 비동기 드라이버를 사용하는 DB URL
        """
        # postgresql -> postgresql+asyncpg
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def redis_url(self) -> str:
        """
        Redis 연결 URL 반환
        
        Returns:
            str: Redis 연결 URL
        """
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def is_production(self) -> bool:
        """
        프로덕션 환경 여부 확인
        
        Returns:
            bool: 프로덕션 환경이면 True
        """
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """
        개발 환경 여부 확인
        
        Returns:
            bool: 개발 환경이면 True
        """
        return self.ENVIRONMENT == "development"


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """
    설정 인스턴스 반환 (의존성 주입용)
    
    Returns:
        Settings: 설정 객체
    """
    return settings
