# StoryProof - 소설 스토리 분석 및 챗봇 시스템

StoryProof는 소설 텍스트를 구조적으로 분석(인물, 사건, 장소)하고, 이를 바탕으로 정확한 답변을 제공하는 RAG(Retrieval-Augmented Generation) 기반 챗봇 시스템입니다.

---

## 🏗️ 프로젝트 구조

```
StoryProof/
├── backend/                    # 백엔드 API 서버 (FastAPI)
│   ├── api/                    # API 엔드포인트
│   ├── core/                   # 설정 (Settings, Config)
│   ├── db/                     # DB 모델 및 세션 관리
│   ├── services/               # 비즈니스 로직 (분석, 챗봇)
│   └── main.py                 # 앱 진입점
├── frontend/                   # 프론트엔드 (React)
├── scripts/                    # 유틸리티 및 관리 스크립트
│   ├── prepare_qa_data.py      # QA 데이터 전처리
│   ├── quick_check_data.py     # 데이터베이스 간단 확인
│   ├── clear_all_data.py       # 데이터 초기화
│   ├── create_index.py         # Pinecone 인덱스 생성
│   └── init_db.py              # DB 테이블 초기화
├── novel_corpus_kr/            # 분석할 소설 텍스트 파일 위치
├── requirements.txt            # Python 의존성 목록
├── .env.example                # 환경 변수 예시
└── README.md                   # 프로젝트 설명서
```

---

## 🛠️ 필수 요건 (Prerequisites)

이 프로젝트를 실행하기 위해 다음 도구들이 필요합니다.

1. **Python 3.10 이상**: `python --version` 으로 확인.
2. **Node.js (LTS)**: `node --version` 으로 확인.
3. **PostgreSQL 15+**: 로컬 설치 또는 Docker 사용 권장.
   - **중요**: Python에서 PostgreSQL 연동을 위해 `psycopg2-binary` 라이브러리를 사용합니다. 설치 시 컴파일 에러가 발생하면 [Troubleshooting](#-문제-해결-troubleshooting) 섹션을 참고하세요.
4. **API 키**:
---

## 🚀 설치 및 실행 가이드

### 1. 프로젝트 설정

```bash
# 1. 프로젝트 클론
git clone <repository_url>
cd StoryProof

# 2. .env 파일 생성 및 키 입력
# .env.example 파일을 .env로 복사하고, 내부의 API 키와 DB 정보를 본인 환경에 맞게 수정하세요.
cp .env.example .env
```

### 2. 백엔드 (Backend) 설정

```bash
# 1. 가상환경 생성 및 활성화 (conda 사용 권장)
conda create -n storyproof python=3.12
conda activate storyproof

# 2. 의존성 패키지 설치
# psycopg2-binary가 포함되어 있어 대부분의 환경에서 별도의 빌드 도구 없이 설치됩니다.
pip install -r requirements.txt

# 3. 데이터베이스 (PostgreSQL) 및 Redis 실행
# Docker 사용 시 (권장): 
docker-compose up -d
# (PostgreSQL: 5432, Redis: 6379 포트 사용)

# 로컬 PostgreSQL 사용 시: 
# 1) PostgreSQL 서비스를 실행합니다.
# 2) 'StoryProof' 이름의 데이터베이스를 생성합니다.
# 3) .env 파일의 DATABASE_URL을 본인의 계정 정보에 맞게 수정합니다.
#    예: DATABASE_URL=postgresql://<user>:<password>@localhost:5432/StoryProof

# 4. 데이터베이스 및 테이블 초기화 (Alembic 마이그레이션 또는 초기화 스크립트)
python scripts/init_db.py

# 5. Pinecone 인덱스 생성 (최초 1회)
python scripts/create_index.py
```

### 3. 서버 실행

**백엔드 (API 서버)**
```bash
# 가상환경 활성화 상태에서
uvicorn backend.main:app --reload
```

**백그라운드 워커 (선택: 소설 분석/업로드 기능 사용 시 필수)**
```bash
# 새 터미널에서 실행
# Windows (solo pool 권장)
celery -A backend.worker.celery_app worker --loglevel=info -P solo

# Mac/Linux:
chmod +x scripts/run_worker.sh
./scripts/run_worker.sh
```

**프론트엔드 (UI)**
```bash
# 새 터미널 열기
cd frontend
npm install  # 최초 1회
npm run dev
```

---

## 📂 주요 스크립트 사용법

`scripts/` 폴더 내의 도구들을 사용하여 데이터를 관리할 수 있습니다. (가상환경 활성화 후 실행)

### 데이터베이스 관리
- **DB 초기화**: `python scripts/init_db.py` - 데이터베이스 테이블 생성 및 초기화
- **데이터 확인**: `python scripts/quick_check_data.py` - 현재 DB의 데이터 개수 확인
- **상세 DB 확인**: `python scripts/check_db.py` - 데이터베이스 상세 정보 조회
- **데이터 초기화**: `python scripts/clear_all_data.py` - DB의 모든 데이터를 삭제(테이블 유지)

### 벡터 인덱스 관리
- **Pinecone 인덱스 생성**: `python scripts/create_index.py` - Pinecone 벡터 인덱스 생성 (최초 1회)
- **Pinecone 리셋**: `python scripts/reset_pinecone.py` - Pinecone 인덱스 초기화
- **챕터 벡터화**: `python scripts/vectorize_chapters.py` - 챕터 임베딩 생성 및 저장

---

## ❓ 문제 해결 (Troubleshooting)

### 1. PostgreSQL & psycopg2 관련 오류
- **`ModuleNotFoundError: No module named 'psycopg2'`**: 
  - `pip install psycopg2-binary`를 실행하여 명시적으로 설치하세요. (binary 버전은 컴파일러가 없는 환경에서도 잘 작동합니다.)
- **`Error: pg_config executable not found`**: 
  - `psycopg2` (소스 빌드 버전) 설치 시 발생하는 오류입니다. `psycopg2-binary`를 사용하면 해결됩니다.
- **`Connection refused` 또는 `Is the server running?`**: 
  - 1. PostgreSQL 서비스가 실행 중인지 확인하세요.
  - 2. `.env`의 `DATABASE_URL`에 적힌 호스트(`localhost`), 포트(`5432`), 계정 이름, 비밀번호가 정확한지 확인하세요.
  - 3. `StoryProof` 데이터베이스가 생성되어 있는지 확인하세요.
- **`순서가 있는 집계함수 mode는 WITHIN GROUP 절이 필요합니다`**:
  - PostgreSQL의 `mode()` 집계 함수를 사용할 때 발생하는 구문 오류입니다.
  - **원인**: `mode()`는 순서가 있는 집계함수로, 반드시 `WITHIN GROUP (ORDER BY ...)` 절과 함께 사용해야 합니다. 
  - **해결**: 직접 SQL을 작성한다면 `SELECT mode() WITHIN GROUP (ORDER BY column_name) FROM table_name;` 형식을 따르세요.
  - **주의**: `users` 테이블의 `mode` 컬럼과 PostgreSQL의 `mode()` 함수를 혼동하지 마세요. 쿼리에서 컬럼 이름으로 사용한다면 반드시 테이블명과 함께 사용(`users.mode`)하거나 큰따옴표(`"mode"`)로 감싸야 합니다.

### 2. 기타 오류
- **ModuleNotFoundError**: 가상환경(`conda` 또는 `venv`)이 활성화되어 있는지 다시 확인하세요.
- **ImportError (Pinecone)**: `pinecone-client`가 올바르게 설치되었는지 `pip list`로 확인하세요. 로컬에 `pinecone.py`라는 파일이 있다면 삭제하거나 이름을 변경해야 합니다.
- **Node/NPM 관련**: `frontend` 폴더 내에서 `npm install`을 실행했는지 확인하세요.

---

