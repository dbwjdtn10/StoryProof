# StoryProof - 프로젝트 아키텍처 상세 분석

**작성일**: 2026-02-03  
**버전**: 1.0

---

## 목차

1. [개요](#1-개요)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [데이터 흐름 다이어그램](#3-데이터-흐름-다이어그램)
4. [주요 컴포넌트 설명](#4-주요-컴포넌트-설명)
5. [데이터베이스 스키마](#5-데이터베이스-스키마)
6. [API 설계](#6-api-설계)
7. [인물 관계도 계획](#7-인물-관계도-계획)
8. [기술 스택 상세](#8-기술-스택-상세)

---

## 1. 개요

### 1.1 프로젝트 목적
StoryProof는 소설 텍스트를 자동으로 분석하여 등장인물, 사건, 장소 등을 구조화하고, RAG(Retrieval-Augmented Generation) 기반 챗봇으로 질의응답을 제공하는 웹 애플리케이션입니다.

### 1.2 핵심 기능
- 📖 **소설 텍스트 업로드 및 자동 분석**
- 🔍 **씬(Scene) 기반 구조화**
- 👥 **인물/장소/아이템/사건 자동 추출**
- 🤖 **RAG 기반 챗봇 질의응답**
- 📊 **인물 관계도 시각화** (구현 예정)
- 💬 **캐릭터 페르소나 챗봇** (구현 예정)

---

## 2. 전체 아키텍처

### 2.1 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        A[React Frontend<br/>TypeScript + Vite]
    end
    
    subgraph "Backend Layer"
        B[FastAPI Server<br/>Python 3.10+]
        C[API Endpoints<br/>auth/novel/chat]
        D[Service Layer]
    end
    
    subgraph "AI/ML Layer"
        E[Google Gemini 2.5 Flash<br/>LLM]
        F[BGE-M3<br/>Embedding Model]
    end
    
    subgraph "Data Layer"
        G[PostgreSQL<br/>Metadata]
        H[Pinecone<br/>Vector DB]
    end
    
    subgraph "Background Processing"
        I[AsyncIO Tasks<br/>Document Processing]
    end
    
    A -.HTTP/REST.-> B
    B --> C
    C --> D
    D --> E
    D --> F
    D --> G
    D --> H
    B --> I
    I --> E
    I --> F
    I --> H
    
    style A fill:#61dafb,stroke:#333,stroke-width:2px
    style B fill:#009688,stroke:#333,stroke-width:2px
    style E fill:#4285f4,stroke:#333,stroke-width:2px
    style G fill:#336791,stroke:#333,stroke-width:2px
    style H fill:#00d4aa,stroke:#333,stroke-width:2px
```

### 2.2 레이어별 역할

| 레이어 | 역할 | 주요 기술 |
|--------|------|-----------|
| **Client Layer** | UI/UX, 사용자 인터랙션 | React, TypeScript, Radix UI |
| **Backend Layer** | API 엔드포인트, 비즈니스 로직 | FastAPI, SQLAlchemy |
| **AI/ML Layer** | 텍스트 분석, 임베딩, 답변 생성 | Google Gemini, BGE-M3 |
| **Data Layer** | 메타데이터 저장, 벡터 검색 | PostgreSQL, Pinecone |
| **Background Processing** | 비동기 문서 처리 | asyncio |

---

## 3. 데이터 흐름 다이어그램

### 3.1 소설 업로드 및 분석 흐름

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant FastAPI
    participant DocumentLoader
    participant SceneChunker
    participant GeminiStructurer
    participant EmbeddingEngine
    participant PostgreSQL
    participant Pinecone
    
    User->>Frontend: 텍스트 파일 업로드
    Frontend->>FastAPI: POST /novels/{id}/chapters
    
    FastAPI->>PostgreSQL: Chapter 레코드 생성<br/>(status=PENDING)
    FastAPI-->>Frontend: 201 Created
    
    FastAPI->>DocumentLoader: 비동기 분석 시작
    
    Note over DocumentLoader: 1. 파일 로드<br/>인코딩 감지<br/>(UTF-8/CP949/EUC-KR)
    
    DocumentLoader->>SceneChunker: 원본 텍스트 전달
    
    Note over SceneChunker: 2. 씬 분할<br/>동적 임계값 기반<br/>문단 유사도 계산
    
    SceneChunker->>GeminiStructurer: 씬 리스트 전달
    
    Note over GeminiStructurer: 3. LLM 구조화<br/>- 인물/장소/아이템 추출<br/>- 사건 요약<br/>- 분위기 분석
    
    GeminiStructurer->>EmbeddingEngine: 구조화된 씬 전달
    
    Note over EmbeddingEngine: 4. 벡터 생성<br/>BGE-M3 임베딩<br/>(1024차원)
    
    EmbeddingEngine->>Pinecone: 벡터 업로드
    EmbeddingEngine->>PostgreSQL: Analysis 저장<br/>(JSONB format)
    
    PostgreSQL-->>FastAPI: 분석 완료
    FastAPI->>PostgreSQL: Chapter 상태 업데이트<br/>(status=COMPLETED)
    
    Frontend->>FastAPI: GET /novels/{id}/chapters/{ch_id}
    FastAPI-->>Frontend: 분석 결과 반환
    Frontend-->>User: 구조화된 데이터 표시
```

### 3.2 RAG 챗봇 질의응답 흐름

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant ChatAPI
    participant ChatbotService
    participant EmbeddingEngine
    participant Pinecone
    participant Gemini
    participant PostgreSQL
    
    User->>Frontend: 질문 입력<br/>"홍길동은 어디로 갔나요?"
    Frontend->>ChatAPI: POST /chat<br/>{question, novel_id}
    
    ChatAPI->>ChatbotService: ask(question)
    
    Note over ChatbotService: 1. 질문 임베딩
    ChatbotService->>EmbeddingEngine: embed(question)
    EmbeddingEngine-->>ChatbotService: query_vector [1024d]
    
    Note over ChatbotService: 2. 유사 씬 검색
    ChatbotService->>Pinecone: query(vector, top_k=5)<br/>+ novel_filter
    Pinecone-->>ChatbotService: 상위 5개 씬<br/>(cosine similarity > 0.5)
    
    Note over ChatbotService: 3. 컨텍스트 구성
    ChatbotService->>ChatbotService: build_context()<br/>(씬 텍스트 결합)
    
    Note over ChatbotService: 4. LLM 답변 생성
    ChatbotService->>Gemini: generate_answer()<br/>+ 컨텍스트 + 질문
    Gemini-->>ChatbotService: 답변 텍스트
    
    Note over ChatbotService: 5. 대화 기록 저장
    ChatbotService->>PostgreSQL: ChatHistory 저장<br/>(user + assistant)
    
    ChatbotService-->>ChatAPI: 답변 반환
    ChatAPI-->>Frontend: 200 OK {answer}
    Frontend-->>User: 답변 표시
```

### 3.3 캐릭터 하이라이팅 흐름

```mermaid
sequenceDiagram
    actor User
    participant ChapterDetail
    participant ChapterBible
    participant Backend
    
    User->>ChapterBible: 사이드바에서<br/>캐릭터 클릭
    ChapterBible->>Backend: GET /analysis<br/>(first_mention_sentence 조회)
    Backend-->>ChapterBible: {first_mention_sentence: 42}
    
    ChapterBible->>ChapterDetail: scrollToSentence(42)
    
    Note over ChapterDetail: 1. 해당 문장 찾기<br/>(CSS selector)
    
    ChapterDetail->>ChapterDetail: 문장에<br/>'highlight-character' 클래스 추가
    
    Note over ChapterDetail: 2. 노란색 배경 애니메이션<br/>(CSS transition)
    
    ChapterDetail->>ChapterDetail: setTimeout(5초)
    
    Note over ChapterDetail: 3. 5초 후<br/>하이라이트 자동 제거
    
    ChapterDetail-->>User: 씬으로 스크롤<br/>+ 휘발성 하이라이팅
```

---

## 4. 주요 컴포넌트 설명

### 4.1 Backend 서비스 모듈

#### 4.1.1 DocumentLoader
> **파일**: `backend/services/analysis/document_loader.py`

**역할**: 텍스트 파일 로드 및 인코딩 자동 감지

**주요 기능**:
- 여러 인코딩 형식 자동 감지 (UTF-8, CP949, EUC-KR)
- UploadFile 객체를 텍스트로 변환
- 에러 핸들링 및 폴백

**핵심 메서드**:
```python
async def load_from_upload(file: UploadFile) -> str:
    """
    자동 인코딩 감지 후 텍스트 반환
    """
```

---

#### 4.1.2 SceneChunker
> **파일**: `backend/services/analysis/scene_chunker.py`

**역할**: 소설 텍스트를 의미 단위의 씬으로 분할

**알고리즘**:
1. 문단별 임베딩 생성 (BGE-M3)
2. 연속된 문단 간 코사인 유사도 계산
3. 유사도가 임계값 이하로 떨어지면 씬 분할
4. 동적 임계값 조정 (평균 유사도 기반)

**핵심 메서드**:
```python
def chunk_by_semantic_similarity(
    text: str,
    threshold: float = 0.7
) -> List[str]:
    """
    의미 기반 씬 분할
    """
```

**특징**:
- ✅ 하드 코딩된 길이 기반 분할 대신 의미 기반
- ✅ 장면 전환을 자동 감지
- ✅ 문맥 보존

---

#### 4.1.3 GeminiStructurer
> **파일**: `backend/services/analysis/gemini_structurer.py`

**역할**: Google Gemini API를 사용한 씬 구조화

**주요 기능**:
1. **씬별 분석** (`structure_scene`)
   - 인물, 장소, 아이템, 사건 추출
   - 분위기, 시간대 분석
   - JSON 형식 응답

2. **전역 엔티티 통합** (`extract_global_entities`)
   - 모든 씬 정보를 통합
   - 인물별 등장 씬 추적
   - 배치 처리 (50개씩)

**데이터 구조**:
```python
@dataclass
class StructuredScene:
    scene_index: int
    original_text: str
    summary: str
    characters: List[str]
    locations: List[str]
    items: List[str]
    key_events: List[str]
    mood: str
    time_period: Optional[str]
```

**시스템 프롬프트**:
```
당신은 소설/스토리의 씬을 분석하여 구조화된 정보를 추출하는 전문가입니다.
주어진 씬에서 다음 정보를 JSON 형식으로 추출하세요:
- summary: 씬의 핵심 요약
- characters: 등장하는 인물 이름들
- locations: 등장하는 장소들
- items: 중요한 아이템/소품들
- key_events: 주요 사건/행동들
- mood: 분위기
- time_period: 시간대 정보
```

**배치 처리 로직**:
- 씬이 50개 초과 시 자동으로 배치 처리
- 각 배치 결과를 병합하여 중복 제거
- API 토큰 제한 회피

---

#### 4.1.4 EmbeddingEngine
> **파일**: `backend/services/analysis/embedding_engine.py`

**역할**: BGE-M3 임베딩 생성 및 Pinecone 업로드

**모델 스펙**:
- 모델명: `BAAI/bge-m3`
- 차원: 1024
- 다국어 지원

**주요 기능**:
1. **임베딩 생성**
   ```python
   def embed(text: str) -> List[float]:
       """텍스트를 1024차원 벡터로 변환"""
   ```

2. **Pinecone 업로드**
   ```python
   def upsert_to_pinecone(
       vector_id: str,
       vector: List[float],
       metadata: Dict
   ):
       """벡터와 메타데이터를 Pinecone에 업로드"""
   ```

**메타데이터 구조**:
```json
{
  "novel_id": 123,
  "chapter_id": 456,
  "scene_index": 5,
  "characters": ["홍길동", "임꺽정"],
  "locations": ["한양"],
  "chunk_text": "원본 텍스트..."
}
```

---

#### 4.1.5 ChatbotService
> **파일**: `backend/services/chatbot_service.py`

**역할**: RAG 기반 질의응답 처리

**파이프라인**:
```mermaid
graph LR
    A[질문 입력] --> B[임베딩 생성]
    B --> C[Pinecone 검색<br/>Top 5 씬]
    C --> D[컨텍스트 구성]
    D --> E[Gemini 답변 생성]
    E --> F[대화 기록 저장]
    
    style A fill:#e1f5ff
    style E fill:#fff4e6
```

**핵심 메서드**:
```python
class ChatbotService:
    def find_similar_chunks(
        question: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5,
        novel_filter: Optional[str] = None
    ) -> List[Dict]:
        """유사 씬 검색"""
    
    def generate_answer(
        question: str,
        context: str
    ) -> str:
        """LLM 답변 생성"""
    
    def ask(question: str) -> str:
        """전체 파이프라인 실행"""
```

**유사도 임계값**:
- 기본값: 0.5 (50%)
- 50% 미만 유사도는 제외
- Top-K: 5개 씬

---

### 4.2 API 엔드포인트

#### 4.2.1 인증 API (`/api/v1/auth`)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/register` | 회원가입 |
| POST | `/login` | 로그인 (JWT 발급) |
| POST | `/refresh` | 토큰 갱신 |
| GET | `/me` | 현재 사용자 정보 |

---

#### 4.2.2 소설 관리 API (`/api/v1/novels`)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/novels` | 새 소설 생성 |
| GET | `/novels` | 소설 목록 조회 (페이지네이션) |
| GET | `/novels/{id}` | 소설 상세 조회 |
| PUT | `/novels/{id}` | 소설 수정 |
| DELETE | `/novels/{id}` | 소설 삭제 |

---

#### 4.2.3 챕터 관리 API (`/api/v1/novels/{id}/chapters`)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/novels/{id}/chapters` | 새 챕터 생성 + 자동 분석 시작 |
| GET | `/novels/{id}/chapters` | 챕터 목록 조회 |
| GET | `/novels/{id}/chapters/{ch_id}` | 챕터 상세 조회 |
| PUT | `/novels/{id}/chapters/{ch_id}` | 챕터 수정 (벡터 유지) |
| POST | `/novels/{id}/chapters/{ch_id}/reanalyze` | 재분석 (벡터 삭제 후 새로 분석) |
| DELETE | `/novels/{id}/chapters/{ch_id}` | 챕터 삭제 |

> **✅ 최근 추가**: 저장(`PUT`)과 재분석(`POST /reanalyze`)이 분리됨
> - **저장**: 미저장 변경사항만 저장, 벡터 유지
> - **재분석**: 기존 벡터 삭제 후 전체 재분석

---

#### 4.2.4 챗봇 API (`/api/v1/chat`)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/chat` | 질문 전송 및 답변 생성 |
| GET | `/chat/history` | 대화 기록 조회 |

**Request Body**:
```json
{
  "question": "홍길동은 어디로 갔나요?",
  "novel_id": 123,
  "session_id": "uuid-v4"
}
```

**Response**:
```json
{
  "answer": "홍길동은 한양으로 향했습니다...",
  "sources": [
    {
      "scene_index": 5,
      "text": "...",
      "similarity": 0.87
    }
  ]
}
```

---

### 4.3 Frontend 컴포넌트

#### 4.3.1 App.tsx
**역할**: 라우팅 및 전역 상태 관리

**주요 라우트**:
- `/login` - 로그인
- `/novels` - 소설 목록
- `/novels/:id/chapters/:chId` - 챕터 상세 (메인 페이지)
- `/chat` - RAG 챗봇

---

#### 4.3.2 ChapterDetail.tsx
**역할**: 챕터 상세 페이지 (메인 UI)

**기능**:
- 본문 표시 및 편집
- 씬별 구조화 데이터 표시
- 저장/재분석 버튼 (분리됨)
- 캐릭터 하이라이팅 (5초 휘발성)

**상태 관리**:
```typescript
const [chapterData, setChapterData] = useState<Chapter>();
const [analysisData, setAnalysisData] = useState<Analysis>();
const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
```

**하이라이팅 로직**:
```typescript
const scrollToSentence = (sentenceNumber: number) => {
  const element = document.querySelector(
    `[data-sentence="${sentenceNumber}"]`
  );
  
  element?.scrollIntoView({ behavior: 'smooth' });
  element?.classList.add('highlight-character');
  
  setTimeout(() => {
    element?.classList.remove('highlight-character');
  }, 5000);
};
```

---

#### 4.3.3 ChapterBible.tsx
**역할**: 사이드바 (인물/장소/아이템/사건)

**기능**:
- 카테고리별 드롭다운
- 캐릭터 클릭 → 하이라이팅
- 등장 횟수 표시
- 색상 구분 (라이트/다크 모드)

**색상 체계**:
- 라이트 모드: 헤더(흰색) / 내용물(옅은 회색)
- 다크 모드: 헤더(검은색) / 내용물(진한 회색)

---

#### 4.3.4 FloatingMenu.tsx
**역할**: 우측 하단 플로팅 메뉴

**버튼**:
- 🤖 챗봇
- 📊 관계도 (구현 예정)
- 💬 캐릭터 챗봇 (구현 예정)

---

## 5. 데이터베이스 스키마

### 5.1 ER 다이어그램

```mermaid
erDiagram
    User ||--o{ Novel : "author"
    User ||--o{ ChatHistory : "user"
    Novel ||--o{ Chapter : "novel"
    Novel ||--o{ Analysis : "novel"
    Chapter ||--o{ Analysis : "chapter"
    Chapter ||--o{ VectorDocument : "chapter"
    
    User {
        int id PK
        string email UK
        string username UK
        string hashed_password
        boolean is_active
        boolean is_verified
        timestamp created_at
    }
    
    Novel {
        int id PK
        int author_id FK
        string title
        text description
        string genre
        text custom_prompt
        boolean is_public
        timestamp created_at
    }
    
    Chapter {
        int id PK
        int novel_id FK
        int chapter_number
        string title
        text content
        int word_count
        string storyboard_status
        int storyboard_progress
        timestamp created_at
    }
    
    Analysis {
        int id PK
        int novel_id FK
        int chapter_id FK
        enum analysis_type
        enum status
        jsonb result
        timestamp created_at
    }
    
    ChatHistory {
        int id PK
        int user_id FK
        int novel_id FK
        string session_id
        string role
        text content
        json meta_data
        timestamp created_at
    }
    
    VectorDocument {
        int id PK
        int novel_id FK
        int chapter_id FK
        string vector_id UK
        int chunk_index
        text chunk_text
        json metadata_json
        timestamp created_at
    }
```

### 5.2 주요 테이블 설명

#### User
- 사용자 계정 정보
- JWT 인증 기반
- 소설 작성자 역할

#### Novel
- 소설 메타데이터
- `custom_prompt`: 사용자 정의 분석 프롬프트 (향후 활용)

#### Chapter
- 회차별 텍스트
- `storyboard_status`: 분석 상태 (PENDING/PROCESSING/COMPLETED/FAILED)
- `storyboard_progress`: 진행률 (0-100)

#### Analysis
- **분석 결과 저장 (JSONB)**
- `result` 필드 구조:
  ```json
  {
    "characters": [
      {
        "name": "홍길동",
        "aliases": ["길동이", "의적"],
        "description": "조선시대 의적",
        "first_appearance": 0,
        "traits": ["정의로움", "용감함"],
        "appearances": [0, 2, 5],
        "appearance_count": 3
      }
    ],
    "locations": [...],
    "items": [...],
    "key_events": [...],
    "scenes": [...]
  }
  ```

#### VectorDocument
- Pinecone 벡터 메타데이터
- `vector_id`: Pinecone ID와 매핑
- PostgreSQL과 Pinecone 동기화

#### ChatHistory
- 대화 기록
- `session_id`: 대화방 그룹화
- `role`: "user" 또는 "assistant"

---

## 6. API 설계

### 6.1 RESTful 원칙

| 원칙 | 적용 사항 |
|------|----------|
| **리소스 중심 URL** | `/novels/{id}/chapters/{ch_id}` |
| **HTTP 메서드** | GET(조회), POST(생성), PUT(수정), DELETE(삭제) |
| **상태 코드** | 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 404 Not Found |
| **페이지네이션** | `?skip=0&limit=10` |
| **필터링** | `?search=keyword&genre=판타지` |

### 6.2 인증 방식

**JWT (JSON Web Token)**
- Access Token: 유효 기간 15분
- Refresh Token: 유효 기간 7일 (현재 미구현)

**헤더 형식**:
```
Authorization: Bearer <access_token>
```

> ⚠️ **보안 이슈**: JWT Secret Key가 기본값 사용 중 → 강력한 랜덤 키 필요

---

## 7. 인물 관계도 계획

### 7.1 개요

**restrored.txt**에 따르면, 캐릭터 관계도 시각화는 **최종 계획 수립 완료** 상태이며 구현 시작 가능합니다.

### 7.2 핵심 전략

#### Phase 1 (MVP)
- **선택 방식**: 체크박스로 2개 이상 캐릭터 선택
- **그래프 라이브러리**: Cytoscape.js
- **비용 최적화**: 공동 등장 빈도 → 상위 N개만 LLM 분석

#### Phase 2 (추후)
- 구간 스냅샷 (시작/중간/끝 3탭)
- 타임라인 리본형 (관계 변화 시각화)
- 이벤트 마커 (살해/배신/키스 등)

---

### 7.3 2단 관계 라벨 체계

캐릭터 간 관계는 **7개 상위 카테고리**로 분류:

| 번호 | 카테고리 | 색상 | 하위 라벨 |
|------|---------|------|----------|
| 1 | **친밀/우호** | 파랑 | 친구, 동료, 신뢰, 보호자 |
| 2 | **로맨스/애정** | 빨강 | 연인, 짝사랑, 배신한 연인 |
| 3 | **가족/혈연** | 초록 | 부모-자식, 형제, 혼인 |
| 4 | **권력/지배** | 보라 | 상사-부하, 스승-제자 |
| 5 | **갈등/적대** | 검정 | 경쟁자, 원수, 복수, 살의 |
| 6 | **거래/이해** | 주황 | 동업, 계약, 동맹 |
| 7 | **모호/미정** | 회색 | 관계 불명 |

---

### 7.4 UX 플로우

```mermaid
sequenceDiagram
    actor User
    participant ChapterBible
    participant RelationshipModal
    participant RelationshipAPI
    participant Gemini
    participant CytoscapeGraph
    
    User->>ChapterBible: [관계도] 버튼 클릭
    ChapterBible->>ChapterBible: 체크박스 표시<br/>[보기] 버튼 비활성
    
    User->>ChapterBible: 캐릭터 2개 선택
    ChapterBible->>ChapterBible: [보기] 버튼 활성화 (파란색)
    
    User->>ChapterBible: [보기] 클릭
    ChapterBible->>RelationshipModal: 오픈 모달
    
    RelationshipModal->>RelationshipAPI: POST /relationships<br/>{character_names: [...]}
    
    Note over RelationshipAPI: 1. Analysis에서<br/>공동 등장 씬 추출
    
    RelationshipAPI->>Gemini: 관계 분석 요청<br/>(상위 N개만)
    Gemini-->>RelationshipAPI: 관계 데이터<br/>(type, strength, certainty)
    
    RelationshipAPI-->>RelationshipModal: {nodes, edges} 반환
    
    RelationshipModal->>CytoscapeGraph: 그래프 렌더링
    CytoscapeGraph-->>User: 관계도 표시
```

---

### 7.5 시각화 규칙

| 속성 | 표현 방식 |
|------|----------|
| **선 굵기** | 관계 강도 (공동 등장 빈도) |
| **선 색상** | 관계 유형 (7가지 카테고리) |
| **선 스타일** | 실선(확실) / 점선(추정) |
| **노드 크기** | 등장 횟수 |

---

### 7.6 API 설계

**엔드포인트**: `POST /novels/{novel_id}/chapters/{chapter_id}/relationships`

**Request**:
```json
{
  "character_names": ["홍길동", "임꺽정", "황진이"]
}
```

**Response**:
```json
{
  "nodes": [
    {
      "id": "홍길동",
      "label": "홍길동",
      "appearance_count": 15
    },
    {
      "id": "임꺽정",
      "label": "임꺽정",
      "appearance_count": 12
    }
  ],
  "edges": [
    {
      "source": "홍길동",
      "target": "임꺽정",
      "relationship_type": "친밀/우호",
      "relationship_subtype": "동료",
      "strength": 0.85,
      "certainty": "확실",
      "co_occurrence_count": 8,
      "scenes": [1, 3, 5, 7, 9, 11, 13, 15]
    }
  ]
}
```

---

### 7.7 구현 계획

#### 백엔드
**파일**: `backend/services/relationship_analyzer.py` (신규 생성)

**핵심 로직**:
1. **공동 등장 빈도 계산**
   ```python
   def calculate_co_occurrence(
       characters: List[str],
       scenes: List[Dict]
   ) -> Dict[tuple, int]:
       """캐릭터 쌍별 공동 등장 횟수 계산"""
   ```

2. **LLM 관계 분석** (상위 N개만)
   ```python
   def analyze_relationship(
       char1: str,
       char2: str,
       scenes: List[Dict]
   ) -> RelationshipEdge:
       """Gemini로 관계 유형 및 강도 분석"""
   ```

3. **그래프 데이터 구성**
   ```python
   def build_relationship_graph(
       characters: List[str],
       analysis: Dict
   ) -> Dict:
       """Cytoscape.js 형식으로 변환"""
   ```

#### 프론트엔드
**파일**: `frontend/src/components/RelationshipGraph.tsx` (신규 생성)

**라이브러리**: `cytoscape`

**설치**:
```bash
npm install cytoscape @types/cytoscape
```

**기본 구조**:
```tsx
import Cytoscape from 'cytoscape';

const RelationshipGraph = ({ nodes, edges }) => {
  useEffect(() => {
    const cy = Cytoscape({
      container: document.getElementById('cy'),
      elements: { nodes, edges },
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#666',
            'label': 'data(label)'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(strength)',
            'line-color': 'data(color)',
            'line-style': 'data(style)'
          }
        }
      ],
      layout: { name: 'cose' }
    });
  }, [nodes, edges]);
  
  return <div id="cy" style={{ width: '100%', height: '600px' }} />;
};
```

---

### 7.8 예상 소요 시간

| 작업 | 시간 |
|------|------|
| 백엔드 API 개발 | 3-4시간 |
| 프론트엔드 UI 개발 | 3-4시간 |
| 통합 테스트 | 1-2시간 |
| **총계** | **8-10시간** |

---

## 8. 기술 스택 상세

### 8.1 Backend

| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.10+ | 런타임 |
| **FastAPI** | Latest | 웹 프레임워크 |
| **SQLAlchemy** | Latest | ORM |
| **Alembic** | Latest | 마이그레이션 |
| **PostgreSQL** | 15+ | 메타데이터 저장 |
| **Pinecone** | Latest | 벡터 검색 |
| **Google Gemini** | 2.5 Flash | LLM (구조화, 챗봇) |
| **BGE-M3** | Latest | 임베딩 모델 (1024d) |
| **asyncio** | Built-in | 백그라운드 작업 |

### 8.2 Frontend

| 기술 | 버전 | 용도 |
|------|------|------|
| **React** | 18 | UI 라이브러리 |
| **TypeScript** | Latest | 타입 안전성 |
| **Vite** | 6.3.5 | 빌드 도구 |
| **Radix UI** | Latest | 접근성 컴포넌트 |
| **Tailwind CSS** | Latest | 스타일링 (추정) |
| **Axios** | Latest | HTTP 클라이언트 |

### 8.3 Infrastructure

| 기술 | 용도 |
|------|------|
| **Docker** | PostgreSQL 컨테이너 |
| **Docker Compose** | 로컬 개발 환경 |

---

## 9. 개선 예정 사항

### 9.1 Critical (즉시 필요)

> [!CAUTION]
> **보안 강화 필요**
> - JWT Secret Key 기본값 → 강력한 랜덤 키 생성
> - Refresh Token 로직 미구현
> - HTTPS 미적용 (프로덕션 시 필요)

> [!WARNING]
> **에러 핸들링 개선**
> - 백그라운드 작업 실패 시 복구 메커니즘 없음
> - Gemini API 실패 시 부분적 처리만
> - Sentry/Rollbar 연동 권장

### 9.2 Important (단기 개선)

- **Celery 도입** (현재 보류)
  - 현재: asyncio.to_thread (페이지 이동 시 작업 손실 가능)
  - 장점: 재시도 정책, 우선순위, 분산 처리
  
- **Redis 캐싱**
  - 동일 질문 매번 Pinecone 검색 → 비용 증가
  - 권장: Redis 캐시 (1시간 TTL)

- **API Rate Limiting**
  - 무제한 API 호출 가능 (DDoS 취약)
  - 권장: SlowAPI 도입 (분당 10회 제한)

### 9.3 Nice to Have (중장기)

- **Hybrid Search**: BM25 + Semantic
- **LangChain 통합**: Conversation Memory, Agent 기반 작업 분할
- **관계도 캐싱**: PostgreSQL + Redis

---

## 10. 참고 문서

| 문서 | 설명 |
|------|------|
| [README.md](file:///c:/KDT_AI/StoryProof-main/README.md) | 프로젝트 개요 및 설치 가이드 |
| [restrored.txt](file:///c:/KDT_AI/StoryProof-main/restrored.txt) | 통합 문서 (현재 상태 요약) |
| [DatabaseSetupGuide.txt](file:///c:/KDT_AI/StoryProof-main/DatabaseSetupGuide.txt) | DB 설정 가이드 |

---

## 11. 실행 가이드

### 11.1 환경 변수 (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/storyproof

# AI Services
GOOGLE_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_env

# Security
JWT_SECRET_KEY=your_secret_key  # ⚠️ 강력한 키로 변경 필요!
```

### 11.2 PostgreSQL 시작

```bash
docker-compose up -d
```

### 11.3 DB 마이그레이션

```bash
alembic upgrade head
```

### 11.4 Backend 실행

```bash
cd c:\KDT_AI\StoryProof-main
python -m uvicorn backend.main:app --reload
```

**URL**: http://localhost:8000

### 11.5 Frontend 실행

```bash
cd c:\KDT_AI\StoryProof-main\frontend
npm install
npm run dev
```

**URL**: http://localhost:5173

---

## 12. 결론

StoryProof는 **AI 기반 소설 분석 플랫폼**으로, Google Gemini와 BGE-M3를 활용하여 소설 텍스트를 자동으로 구조화하고 RAG 챗봇으로 질의응답을 제공합니다.

**현재 핵심 기능**:
- ✅ 씬 기반 자동 분석
- ✅ 인물/장소/아이템/사건 추출
- ✅ RAG 챗봇 질의응답
- ✅ 캐릭터 하이라이팅

**구현 예정**:
- 🚧 인물 관계도 시각화 (Cytoscape.js)
- 📝 캐릭터 페르소나 챗봇
- ⏸️ Celery 백그라운드 작업 (보류)

**아키텍처 강점**:
- 마이크로서비스 지향 설계
- 명확한 레이어 분리
- 확장 가능한 구조

**개선 필요 영역**:
- 보안 강화 (JWT, HTTPS)
- 에러 핸들링 개선
- 캐싱 전략 도입

---

**작성자**: AI Assistant  
**문서 버전**: 1.0  
**최종 수정**: 2026-02-03
