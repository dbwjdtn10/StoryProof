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
4. **API 키**:
   - **Google Gemini API Key**: [AI Studio](https://aistudio.google.com/app/apikey)에서 발급.
   - **Pinecone API Key**: [Pinecone](https://www.pinecone.io/)에서 발급 ('story-child-index-384' 인덱스 필요).
5. **Redis**: (선택 사항, 백그라운드 작업용) Docker compose 사용 시 자동 설치됨.

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
# 1. 가상환경 생성 및 활성화(conda 사용 권장)
conda create -n storyproof python=3.12
conda activate storyproof

# 2. 의존성 패키지 설치
pip install -r requirements.txt

# 3. 데이터베이스(PostgreSQL) 및 Redis 실행
# Docker 사용 시 (권장): 
docker-compose up -d
# (PostgreSQL: 5432, Redis: 6379 포트 사용)

# 로컬 사용 시: 
# PostgreSQL 서비스를 실행하고, Redis 서버도 별도로 실행해야 합니다.

# 4. 데이터베이스 및 테이블 초기화
python scripts/init_db.py

# 5. Pinecone 인덱스 생성 (최초 1회, 384로 변환되어 새로이 인덱스 만들어야함)
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
# powershell
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

- **데이터 확인**: `python scripts/quick_check_data.py` - 현재 DB의 데이터 개수 확인.
- **데이터 초기화**: `python scripts/clear_all_data.py` - DB의 모든 데이터를 삭제(테이블 유지).
- **소설 데이터 전처리**: `python scripts/prepare_qa_data.py` - `novel_corpus_kr/` 폴더의 소설들을 분석하여 임베딩 데이터 생성.

---

## ❓ 문제 해결 (Troubleshooting)

- **ModuleNotFoundError**: 가상환경(`venv`)이 활성화되어 있는지 확인하세요.
- **DB 연결 오류**: `.env` 파일의 `DATABASE_URL`이 올바른지, PostgreSQL 서버가 켜져 있는지 확인하세요.
- **ImportError (Pinecone)**: `pinecone-client`가 올바르게 설치되었는지 `pip list`로 확인하세요. 로컬에 `pinecone.py`라는 파일이 있다면 삭제하거나 이름을 변경해야 합니다.

---
