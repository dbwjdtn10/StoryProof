# StoryProof - AI 기반 소설 분석 및 창작 지원 플랫폼

StoryProof는 소설 텍스트를 구조적으로 분석(인물, 사건, 장소)하고, RAG(Retrieval-Augmented Generation) 기반 챗봇, 캐릭터 대화, 이미지 생성, 스토리 예측 등 다양한 AI 기능을 제공하는 풀스택 웹 애플리케이션입니다.

---

## 주요 기능

- **소설 업로드 및 관리**: txt/docx/pdf 파일 업로드, 챕터 단위 관리 및 병합
- **스토리보드 분석**: 업로드된 텍스트를 자동으로 청킹 → 구조 분석 → 벡터 임베딩 (Celery 비동기 처리)
- **RAG 챗봇**: 소설 내용 기반 Q&A (Vector + BM25 하이브리드 검색, 스트리밍 응답)
- **캐릭터 채팅**: AI가 소설 속 캐릭터의 페르소나를 생성하고, 해당 캐릭터로서 대화
- **일관성 분석**: 플롯 모순, 캐릭터 설정 충돌 등 스토리 일관성 검증
- **스토리 예측**: 현재 맥락을 기반으로 다음 전개 방향 예측
- **이미지 생성**: Google Imagen API를 활용한 캐릭터/아이템/장소 이미지 생성
- **테마 지원**: 라이트/다크/세피아 3종 테마

---

## 프로젝트 구조

```
StoryProof/
├── backend/                        # FastAPI 백엔드
│   ├── api/v1/endpoints/           # API 엔드포인트
│   │   ├── auth.py                 # 인증 (회원가입/로그인/프로필)
│   │   ├── novel.py                # 소설/챕터 CRUD, 파일 업로드
│   │   ├── chat.py                 # RAG 기반 Q&A 챗봇
│   │   ├── character_chat.py       # 캐릭터 채팅 (페르소나 생성/대화)
│   │   ├── analysis.py             # 일관성 분석
│   │   ├── prediction.py           # 스토리 예측
│   │   └── images.py               # 이미지 생성
│   ├── core/                       # 설정 및 보안
│   ├── db/                         # DB 모델 및 세션 관리
│   ├── schemas/                    # Pydantic 스키마
│   ├── services/                   # 비즈니스 로직
│   │   ├── analysis/               # 분석 엔진 (임베딩, 청킹, 구조화)
│   │   ├── chatbot_service.py      # RAG 챗봇 서비스
│   │   ├── novel_service.py        # 소설 관리 서비스
│   │   ├── character_chat_service.py # 캐릭터 채팅 서비스
│   │   ├── image_service.py        # 이미지 생성 서비스
│   │   ├── analysis_service.py     # 분석 서비스
│   │   ├── agent.py                # 일관성/예측 에이전트
│   │   └── auth_service.py         # 인증 서비스
│   ├── worker/                     # Celery 백그라운드 워커
│   │   ├── tasks.py                # 스토리보드 처리 태스크
│   │   └── prediction_tasks.py     # 스토리 예측 태스크
│   └── main.py                     # 앱 진입점
├── frontend/                       # React + TypeScript 프론트엔드
│   ├── src/
│   │   ├── api/                    # API 클라이언트 모듈
│   │   ├── components/             # React 컴포넌트
│   │   ├── contexts/               # Context Providers
│   │   ├── hooks/                  # Custom Hooks
│   │   └── types/                  # TypeScript 타입 정의
│   └── package.json
├── scripts/                        # 유틸리티 스크립트
├── alembic/                        # DB 마이그레이션
├── requirements.txt                # Python 의존성
├── .env.example                    # 환경 변수 예시
└── README.md
```

---

## 기술 스택

### 백엔드
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL + SQLAlchemy 2.0 + Alembic
- **Vector DB**: Pinecone
- **AI/LLM**: Google Gemini 2.5 Flash (분석/챗봇), Imagen 4.0 (이미지 생성)
- **Embedding**: multilingual-e5-small-ko (sentence-transformers)
- **검색**: Vector (82.5%) + BM25 (17.5%) 하이브리드 검색, 선택적 리랭킹
- **비동기 처리**: Celery + Redis
- **인증**: JWT (python-jose) + Argon2 해싱
- **한국어 NLP**: kiwipiepy (형태소 분석)

### 프론트엔드
- **Framework**: React 18 + TypeScript
- **Build**: Vite
- **UI**: Radix UI + Tailwind CSS (Shadcn/ui)
- **에디터**: TipTap (리치 텍스트)
- **차트**: Recharts
- **알림**: Sonner (toast)
- **HTTP**: Axios

---

## 필수 요건

1. **Python 3.10+**
2. **Node.js (LTS)**
3. **PostgreSQL 15+**
4. **Redis** (Celery 브로커용)
5. **API 키**:
   - Google AI (Gemini + Imagen)
   - Pinecone

---

## 설치 및 실행

### 1. 프로젝트 설정

```bash
git clone https://github.com/dbwjdtn10/StoryProof.git
cd StoryProof
cp .env.example .env
# .env 파일에 API 키 및 DB 정보 입력
```

### 2. 백엔드 설정

```bash
# 가상환경 생성 및 활성화
conda create -n storyproof python=3.12
conda activate storyproof

# 의존성 설치
pip install -r requirements.txt

# DB 및 Redis 실행 (Docker 사용 시)
docker-compose up -d

# DB 테이블 초기화
python scripts/init_db.py

# Pinecone 인덱스 생성 (최초 1회)
python scripts/create_index.py
```

### 3. 서버 실행

```bash
# 백엔드 API 서버
uvicorn backend.main:app --reload

# Celery 워커 (새 터미널)
# Windows:
celery -A backend.worker.celery_app worker --loglevel=info -P solo
# Mac/Linux:
chmod +x scripts/run_worker.sh && ./scripts/run_worker.sh

# 프론트엔드 (새 터미널)
cd frontend
npm install  # 최초 1회
npm run dev
```

---

## API 엔드포인트

| 카테고리 | 메서드 | 경로 | 설명 |
|---------|--------|------|------|
| **인증** | POST | `/api/v1/auth/register` | 회원가입 |
| | POST | `/api/v1/auth/login` | 로그인 (JWT 발급) |
| | GET | `/api/v1/auth/profile` | 프로필 조회 |
| **소설** | POST | `/api/v1/novels/` | 소설 생성 |
| | GET | `/api/v1/novels/` | 소설 목록 (검색/장르 필터) |
| | GET/PUT/DELETE | `/api/v1/novels/{id}` | 소설 조회/수정/삭제 |
| **챕터** | POST | `/api/v1/novels/{id}/chapters` | 챕터 추가 |
| | GET/PUT/DELETE | `/api/v1/novels/{id}/chapters/{ch_id}` | 챕터 조회/수정/삭제 |
| | POST | `/api/v1/novels/{id}/chapters/merge` | 챕터 병합 |
| | POST | `/api/v1/novels/{id}/upload` | 파일 업로드 (txt/docx/pdf) |
| **챗봇** | POST | `/api/v1/chat/ask` | RAG Q&A (스트리밍) |
| **캐릭터 채팅** | POST | `/api/v1/character-chat/rooms` | 채팅방 생성 |
| | GET | `/api/v1/character-chat/rooms` | 채팅방 목록 |
| | POST | `/api/v1/character-chat/rooms/{id}/messages` | 메시지 전송 |
| | POST | `/api/v1/character-chat/generate-persona` | 페르소나 생성 |
| **분석** | POST | `/api/v1/analysis/consistency` | 일관성 분석 요청 |
| | GET | `/api/v1/analysis/task/{task_id}` | 분석 결과 조회 |
| **예측** | POST | `/api/v1/prediction/request` | 스토리 예측 요청 |
| | GET | `/api/v1/prediction/task/{task_id}` | 예측 결과 조회 |
| **이미지** | POST | `/api/v1/images/generate` | 엔티티 이미지 생성 |
| **헬스** | GET | `/health` | 서버 상태 확인 |

---

## 스크립트

| 스크립트 | 설명 |
|---------|------|
| `scripts/init_db.py` | DB 테이블 생성 및 초기화 |
| `scripts/create_index.py` | Pinecone 벡터 인덱스 생성 |
| `scripts/quick_check_data.py` | DB 데이터 현황 확인 |
| `scripts/check_db.py` | DB 상세 정보 조회 |
| `scripts/clear_all_data.py` | 전체 데이터 삭제 (테이블 유지) |
| `scripts/reset_pinecone.py` | Pinecone 인덱스 초기화 |
| `scripts/vectorize_chapters.py` | 챕터 임베딩 생성 |
| `scripts/setup_gcp.sh` | GCP 인스턴스 초기 설정 |

---

## 문제 해결

### PostgreSQL 관련
- **`ModuleNotFoundError: No module named 'psycopg2'`**: `pip install psycopg2-binary` 실행
- **`Connection refused`**: PostgreSQL 서비스 실행 여부, `.env`의 `DATABASE_URL` 확인
- **`mode` 관련 SQL 오류**: `users` 테이블의 `mode` 컬럼을 쿼리 시 `users.mode` 또는 `"mode"`로 명시

### 기타
- **ModuleNotFoundError**: 가상환경 활성화 확인
- **ImportError (Pinecone)**: `pinecone-client` 설치 확인, 로컬에 `pinecone.py` 파일이 있으면 삭제
- **Node/NPM**: `frontend/` 폴더에서 `npm install` 실행 확인
