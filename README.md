# StoryProof - 소설 스토리 분석 및 챗봇 시스템

StoryProof는 소설 텍스트를 분석하여 구조화된 정보(인물, 사건, 장소)를 추출하고, 이를 바탕으로 질문에 답변하는 RAG(Retrieval-Augmented Generation) 기반 챗봇 시스템입니다.

이 문서는 **모든 팀원이 각자의 로컬 환경(Windows/Mac)에서 프로젝트를 실행할 수 있도록** 상세하게 작성되었습니다.

---

## 🏗️ 프로젝트 구조

```
StoryProof/
├── backend/                    # 백엔드 API 서버
│   ├── api/                   # API 엔드포인트
│   ├── core/                  # 핵심 설정 (config, security)
│   ├── db/                    # 데이터베이스 모델 및 세션
│   ├── schemas/               # Pydantic 스키마
│   ├── services/              # 비즈니스 로직
│   │   ├── analysis/         # 🆕 분석 모듈 (리팩토링됨)
│   │   │   ├── document_loader.py    # 파일 로딩
│   │   │   ├── scene_chunker.py      # 씬 분할
│   │   │   ├── gemini_structurer.py  # LLM 구조화
│   │   │   └── embedding_engine.py   # 벡터 검색
│   │   └── chatbot_service.py
│   ├── worker/                # 백그라운드 작업
│   └── main.py               # FastAPI 앱 진입점
├── frontend/                  # React 프론트엔드
├── scripts/                   # 유틸리티 스크립트
├── alembic/                   # DB 마이그레이션
├── requirements.txt           # Python 의존성
├── .env.example              # 환경 변수 템플릿
└── docker-compose.yml        # PostgreSQL Docker 설정
```

---

## 🛠️ 기술 스택

### Backend
- **Python 3.10+** - 프로그래밍 언어
- **FastAPI** - 웹 프레임워크
- **SQLAlchemy** - ORM (Object-Relational Mapping)
- **Alembic** - 데이터베이스 마이그레이션
- **Pydantic** - 데이터 검증

### Frontend
- **React 18** - UI 라이브러리
- **TypeScript** - 타입 안전성
- **Vite** - 빌드 도구
- **Tailwind CSS** - 스타일링

### Database
- **PostgreSQL 15+** - 관계형 데이터베이스 (메타데이터 저장)
- **Pinecone** - 벡터 데이터베이스 (임베딩 검색)

### AI Models
- **Google Gemini 2.5 Flash** - 텍스트 생성 및 구조화
- **BAAI/bge-m3** - 다국어 임베딩 모델

---

## 🚀 1. 사전 준비 (Prerequisites)

프로젝트를 시작하기 전에 다음 도구들이 설치되어 있어야 합니다.

### 필수 설치 항목

1. **Git** - 버전 관리
   - [다운로드](https://git-scm.com/downloads)

2. **Python 3.10 이상**
   - [다운로드](https://www.python.org/downloads/)
   - ⚠️ **중요**: 설치 시 "Add Python to PATH" 체크박스를 꼭 선택하세요!
   - 설치 확인: `python --version`

3. **Node.js (LTS 버전)**
   - [다운로드](https://nodejs.org/ko/)
   - 설치 확인: `node --version` 및 `npm --version`

4. **PostgreSQL 데이터베이스** (아래 중 하나 선택)
   - **방법 A (권장)**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치
     - 간편하고 팀원 간 환경 통일 가능
   - **방법 B**: [PostgreSQL](https://www.postgresql.org/download/) 직접 설치
     - 설치 시 비밀번호를 기억해두세요

---

## 📥 2. 프로젝트 다운로드 (Git Clone)

터미널(Windows: PowerShell, Mac: Terminal)을 열고 다음 명령어를 실행합니다.

```bash
# 1. 프로젝트 복제 (실제 GitHub 주소로 변경)
git clone <여기에_깃허브_주소를_입력하세요>

# 2. 프로젝트 폴더로 이동
cd StoryProof
```

---

## ⚙️ 3. 환경 변수 설정 (.env)

프로젝트는 API 키와 데이터베이스 접속 정보를 `.env` 파일에서 관리합니다.

### 3.1 .env 파일 생성

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Mac/Linux
cp .env.example .env
```

### 3.2 .env 파일 편집

`.env` 파일을 텍스트 에디터로 열어 다음 항목들을 채워넣습니다.

```ini
# ===== Google Gemini API =====
# https://aistudio.google.com/app/apikey 에서 발급
GOOGLE_API_KEY=AIzaSy...

# ===== Pinecone 벡터 DB =====
# https://www.pinecone.io/ 에서 무료 계정 생성 후 발급
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=storyproof-index

# ===== PostgreSQL 데이터베이스 =====
# Docker 사용 시: 아래 기본값 그대로 사용
# 직접 설치 시: 본인이 설정한 비밀번호로 변경
DATABASE_URL=postgresql://postgres:1234!@#$@localhost:5432/StoryProof

# 비밀번호에 특수문자가 있으면 URL 인코딩 필요:
# ! → %21, @ → %40, # → %23, $ → %24
# 예: 1234!@#$ → 1234%21%40%23%24
```

### 3.3 Pinecone 인덱스 생성

1. [Pinecone 콘솔](https://app.pinecone.io/)에 로그인
2. "Create Index" 클릭
3. 설정:
   - **Index Name**: `storyproof-index`
   - **Dimensions**: `1024`
   - **Metric**: `dotproduct`
   - **Cloud**: `AWS` (무료)
   - **Region**: 가장 가까운 지역 선택

---

## 💾 4. 데이터베이스 실행

백엔드를 실행하기 전에 PostgreSQL 데이터베이스가 실행 중이어야 합니다.

### 방법 A: Docker 사용 (권장)

```bash
# Docker Desktop이 실행 중인지 확인 후

# 1. PostgreSQL 컨테이너 시작
docker-compose up -d

# 2. 실행 확인
docker ps
# postgres:16 컨테이너가 보이면 성공

# 3. 중지하려면
docker-compose down
```

### 방법 B: 로컬 PostgreSQL 사용

1. PostgreSQL 서비스가 실행 중인지 확인
2. pgAdmin 또는 psql로 접속
3. `StoryProof` 데이터베이스 생성:
   ```sql
   CREATE DATABASE "StoryProof";
   ```
4. `.env` 파일의 `DATABASE_URL`을 본인 설정에 맞게 수정

---

## 🐍 5. 백엔드 실행 (Backend)

새 터미널 창을 열고 다음 순서대로 진행합니다.

### 5.1 가상환경 생성 및 활성화

```bash
# 1. 가상환경 생성 (최초 1회만)
python -m venv venv

# 2. 가상환경 활성화
# Windows (PowerShell):
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate

# ✅ 성공하면 터미널 앞에 (venv) 표시됨
```

### 5.2 Python 패키지 설치

```bash
# requirements.txt의 모든 패키지 설치
pip install -r requirements.txt

# ⏱️ 첫 설치는 5-10분 정도 소요될 수 있습니다
# (sentence-transformers가 큰 모델을 다운로드하기 때문)
```

### 5.3 데이터베이스 초기화

데이터베이스 테이블을 생성하는 방법은 두 가지가 있습니다.

#### 방법 A: 초기화 스크립트 사용 (권장)

```bash
# 데이터베이스 상태 확인
python scripts/check_db.py

# 데이터베이스 초기화 (테이블 생성)
python scripts/init_db.py

# Alembic 마이그레이션 히스토리 설정
alembic stamp head

# ✅ "데이터베이스 초기화 완료!" 메시지가 보이면 성공
```

#### 방법 B: Alembic 마이그레이션 사용

```bash
# 데이터베이스에 필요한 테이블 생성
alembic upgrade head

# ✅ "Running upgrade ... -> ..., done" 메시지가 보이면 성공
```

#### 🔄 데이터베이스 완전 리셋 (문제 발생 시)

```bash
# ⚠️ 주의: 모든 데이터가 삭제됩니다!
python scripts/init_db.py --reset

# Alembic 마이그레이션 히스토리 재설정
alembic stamp head

# 상태 확인
python scripts/check_db.py
```


### 5.4 백엔드 서버 실행

```bash
# FastAPI 서버 시작 (개발 모드)
uvicorn backend.main:app --reload

# ✅ "Application startup complete" 메시지 확인
# 🌐 http://localhost:8000 에서 접속 가능
# 📚 http://localhost:8000/docs 에서 API 문서 확인 가능
```

---

## ⚛️ 6. 프론트엔드 실행 (Frontend)

**새로운 터미널 창**을 열고 다음을 진행합니다.

```bash
# 1. frontend 폴더로 이동
cd frontend

# 2. Node.js 패키지 설치 (최초 1회)
npm install

# 3. 개발 서버 실행
npm run dev

# ✅ "Local: http://localhost:5173" 메시지 확인
# 🌐 브라우저에서 해당 주소로 접속
```

---

## 🧪 7. 동작 확인

### 백엔드 확인
1. 브라우저에서 http://localhost:8000/docs 접속
2. Swagger UI에서 API 테스트 가능

### 프론트엔드 확인
1. 브라우저에서 http://localhost:5173 접속
2. 로그인/회원가입 화면이 보이면 성공

### 전체 시스템 테스트
1. 회원가입 → 로그인
2. 소설 업로드 (TXT 파일)
3. 챕터 분석 대기
4. 챗봇에서 질문하기

---

## ❓ 문제 해결 (Troubleshooting)

### 🔴 `alembic upgrade head` 실패

**증상**: `sqlalchemy.exc.OperationalError`, `ProgrammingError`, 또는 연결 오류

**원인 1: PostgreSQL이 실행되지 않음**

```bash
# Docker 사용 시
docker ps
# postgres 컨테이너가 보이지 않으면:
docker-compose up -d

# 로컬 설치 시
# Windows: 작업 관리자 → 서비스 → postgresql 확인
# Mac: brew services list
```

**원인 2: DATABASE_URL이 잘못됨**

1. `.env` 파일 확인
   - 사용자명, 비밀번호, 포트, 데이터베이스명이 정확한지 확인
   - 특수문자는 URL 인코딩 필요 (! → %21, @ → %40, # → %23, $ → %24)

2. 데이터베이스 연결 테스트
   ```bash
   python scripts/check_db.py
   ```

**원인 3: 데이터베이스가 생성되지 않음**

```bash
# PostgreSQL에 접속하여 데이터베이스 생성
# Docker 사용 시:
docker exec -it storyproof-postgres psql -U postgres
CREATE DATABASE "StoryProof";
\q

# 또는 pgAdmin 사용
```

**원인 4: 스키마 불일치 (테이블 형식이 다름)**

```bash
# 데이터베이스 완전 리셋
python scripts/init_db.py --reset

# Alembic 히스토리 재설정
alembic stamp head

# 상태 확인
python scripts/check_db.py
```

---

### 🔴 데이터베이스 스키마 오류

**증상**: `column "..." does not exist`, `relation "..." does not exist`

**해결 방법**:

```bash
# 1. 현재 데이터베이스 상태 확인
python scripts/check_db.py

# 2. 문제가 있으면 데이터베이스 리셋
python scripts/init_db.py --reset

# 3. Alembic 히스토리 설정
alembic stamp head

# 4. 백엔드 서버 재시작
uvicorn backend.main:app --reload
```

**주의**: `--reset` 옵션은 모든 데이터를 삭제하므로 프로덕션 환경에서는 사용하지 마세요!

---

### 🔴 `ModuleNotFoundError` 또는 `ImportError`

**증상**: `No module named 'fastapi'` 등

**해결 방법**:
1. 가상환경이 활성화되어 있는지 확인 (터미널에 `(venv)` 표시)
2. 가상환경 재활성화 후 패키지 재설치
   ```bash
   # 가상환경 비활성화
   deactivate
   
   # 재활성화
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
   
   # 패키지 재설치
   pip install -r requirements.txt
   ```

---

### 🔴 `sentence-transformers` 설치 오류

**증상**: PyTorch 관련 에러

**해결 방법**:
```bash
# PyTorch 먼저 설치
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 그 다음 requirements.txt 설치
pip install -r requirements.txt
```

---

### 🔴 Pinecone 연결 오류

**증상**: `PineconeException` 또는 인덱스를 찾을 수 없음

**해결 방법**:
1. `.env`의 `PINECONE_API_KEY`가 올바른지 확인
2. Pinecone 콘솔에서 `storyproof-index` 인덱스가 생성되어 있는지 확인
3. 인덱스 설정 확인:
   - Dimensions: 1024
   - Metric: dotproduct

---

### 🔴 포트 충돌 오류

**증상**: `Address already in use` 또는 `Port 8000 is already allocated`

**해결 방법**:
```bash
# Windows: 포트 사용 중인 프로세스 확인 및 종료
netstat -ano | findstr :8000
taskkill /PID <프로세스ID> /F

# Mac/Linux:
lsof -ti:8000 | xargs kill -9
```

---

## 📝 개발 가이드

### 코드 수정 시
- **백엔드**: `--reload` 옵션으로 자동 재시작됨
- **프론트엔드**: Vite의 HMR(Hot Module Replacement)로 즉시 반영

### API 테스트
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 데이터베이스 스키마 변경
```bash
# 1. models.py 수정
# 2. 마이그레이션 파일 생성
alembic revision --autogenerate -m "변경 내용 설명"

# 3. 마이그레이션 적용
alembic upgrade head
```

### 데이터베이스 관리 명령어
```bash
# 데이터베이스 상태 확인
python scripts/check_db.py

# 데이터베이스 초기화 (테이블 생성)
python scripts/init_db.py

# 데이터베이스 완전 리셋 (⚠️ 모든 데이터 삭제)
python scripts/init_db.py --reset

# 테스트 데이터 포함 초기화
python scripts/init_db.py --with-seed-data

# 마이그레이션 히스토리 확인
alembic history

# 현재 마이그레이션 버전 확인
alembic current

# 특정 버전으로 다운그레이드
alembic downgrade <revision_id>
```


### 새로운 Python 패키지 추가
```bash
# 1. 패키지 설치
pip install 패키지명

# 2. requirements.txt 업데이트
pip freeze > requirements.txt
```

---

## 🔒 보안 주의사항

- ⚠️ `.env` 파일은 절대 Git에 커밋하지 마세요
- ⚠️ API 키는 팀원과 안전한 방법으로 공유하세요 (Slack DM, 암호화된 파일 등)
- ⚠️ 프로덕션 환경에서는 강력한 비밀번호 사용

---

## 📚 추가 리소스

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React 공식 문서](https://react.dev/)
- [Pinecone 문서](https://docs.pinecone.io/)
- [Google Gemini API 문서](https://ai.google.dev/docs)

---

## 👥 팀 협업

### Git 워크플로우
```bash
# 1. 최신 코드 가져오기
git pull origin main

# 2. 새 브랜치 생성
git checkout -b feature/기능명

# 3. 작업 후 커밋
git add .
git commit -m "feat: 기능 설명"

# 4. 푸시
git push origin feature/기능명

# 5. GitHub에서 Pull Request 생성
```

### 문제 발생 시
1. 에러 메시지 전체를 복사
2. 팀 채널에 공유
3. `.env` 파일 내용은 공유하지 말 것!

---

## 📞 문의

프로젝트 관련 문의사항은 팀 리더에게 연락하세요.
