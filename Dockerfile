# Backend Dockerfile (Optimized for Cloud Run)

# -------------------------------------------------------------------
# Stage 1: Builder (의존성 패키지 빌드)
# -------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# 시스템 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사
COPY requirements.txt .

# 1. CPU 전용 PyTorch 설치 (용량 대폭 절감)
# Cloud Run은 GPU가 없으므로 cu118/cu121 버전은 불필요
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2. 나머지 의존성 설치 (User Base에 설치)
# --user 옵션을 사용하여 root가 아닌 사용자 영역에 설치 -> 나중에 복사하기 위함
RUN pip install --no-cache-dir --user -r requirements.txt

# -------------------------------------------------------------------
# Stage 2: Runner (실제 실행 이미지)
# -------------------------------------------------------------------
FROM python:3.11-slim as runner

WORKDIR /app

# 런타임에 필요한 시스템 패키지 설치 (최소화)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Builder에서 설치한 파이썬 패키지 복사
COPY --from=builder /root/.local /root/.local

# PATH 환경변수 설정 (User Base bin 포함)
ENV PATH=/root/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini .

# 정적 파일 디렉토리 생성
RUN mkdir -p backend/static/images

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Cloud Run 포트 노출
EXPOSE 8080

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
