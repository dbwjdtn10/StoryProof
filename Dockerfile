# StoryProof Backend (API 서버 + Celery 워커 공용 이미지)
#
# 빌드:  docker build -t storyproof-backend .
# 실행:  docker-compose up -d (권장)

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/data/hf_cache

WORKDIR /app

# 시스템 의존성 (psycopg2 / 빌드 도구)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드
COPY backend ./backend
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts

RUN mkdir -p data/uploads logs backend/static/images

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD curl -sf http://localhost:8000/health || exit 1

# 기본 명령: API 서버 (워커는 compose에서 command 오버라이드)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
