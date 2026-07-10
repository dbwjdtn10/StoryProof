# StoryProof 파트너 API 연동 가이드

인터넷서점/웹소설 플랫폼 파트너를 위한 B2B API 문서입니다.
Swagger UI: `https://<host>/docs` (Partner API 태그)

## 인증

모든 요청에 발급받은 API 키를 `X-API-Key` 헤더로 전달합니다.

```
X-API-Key: sp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- 키는 발급 시 1회만 노출됩니다 (서버에는 해시만 저장).
- 401: 키 누락/무효/만료 · 403: 파트너 비활성 · 429: 레이트 리밋/월간 쿼터 초과

## 워크플로

### 1. 원고 접수

```http
POST /api/partner/v1/manuscripts
Content-Type: application/json
X-API-Key: <key>

{
  "title": "달빛 조각사",
  "genre": "판타지",
  "external_id": "kakao-work-12345",
  "chapters": [
    { "chapter_number": 1, "title": "1화. 시작", "content": "..." },
    { "chapter_number": 2, "title": "2화. 각성", "content": "..." }
  ]
}
```

응답 `202`:
```json
{ "manuscript_id": 42, "external_id": "kakao-work-12345", "chapter_ids": [101, 102], "status": "processing" }
```

접수 즉시 회차별 청킹 → 구조 분석 → 벡터 임베딩이 백그라운드로 진행됩니다.
**과금: 회차당 1 unit**

### 1-1. 원고 파일 접수 (EPUB/TXT/DOCX/PDF)

```http
POST /api/partner/v1/manuscripts/upload
Content-Type: multipart/form-data
X-API-Key: <key>

file=@book.epub  title="달빛 조각사"  genre="판타지"  external_id="kakao-work-12345"
```

- **EPUB**: spine 문서 단위로 자동 회차 분리 (전자책 표준 워크플로)
- TXT/DOCX/PDF: 전체를 1개 회차로 접수
- 응답 형식은 원고 접수와 동일 (`202` + `chapter_ids`)

**과금: 생성 회차당 1 unit**

### 2. 처리 상태 확인 (무과금)

```http
GET /api/partner/v1/manuscripts/42/status
```

```json
{
  "manuscript_id": 42, "title": "달빛 조각사", "ready": true,
  "chapters": [
    { "chapter_id": 101, "chapter_number": 1, "status": "COMPLETED", "progress": 100, "error": null }
  ]
}
```

`ready: true`가 되면 Q&A/일관성 검증을 사용할 수 있습니다.

### 3. 작품 Q&A (독자용 챗봇)

```http
POST /api/partner/v1/manuscripts/42/qa

{ "question": "주인공이 왜 길드를 떠났어?", "chapter_id": 101 }
```

- `chapter_id`를 지정하면 **해당 회차까지의 내용만** 근거로 답변 → 독자가 읽은
  지점 이후의 스포일러를 차단할 수 있습니다.
- 답변 근거를 작품 내에서 찾지 못하면 `found_context: false`로 응답합니다
  (LLM 학습 데이터 기반 환각 방지).

**과금: 질문당 1 unit**

### 4. 설정 일관성 검증 (편집자/작가 스튜디오용)

```http
POST /api/partner/v1/manuscripts/42/consistency

{ "text": "아직 등록하지 않은 신규 회차 원고 전문..." }
```

또는 등록된 회차 검증: `{ "chapter_id": 102 }`

응답 `202`: `{ "task_id": "abc-123", "status": "PENDING" }`

결과 조회 (무과금):
```http
GET /api/partner/v1/tasks/abc-123
→ { "status": "COMPLETED", "result": { ...모순 목록/근거... } }
```

**과금: 검증 건당 1 unit**

### 4-1. 웹훅 (폴링 대체, 무과금)

처리 완료 이벤트를 파트너 서버로 push 받으려면 웹훅을 등록합니다.

```http
PUT /api/partner/v1/webhook
{ "url": "https://partner.example.com/callbacks/storyproof" }
→ { "url": "...", "secret": "<64자 hex — 이 응답에서만 확인 가능>" }
```

이후 이벤트 발생 시 등록 URL로 POST 전송됩니다:

```http
POST <your-url>
X-StoryProof-Event: manuscript.chapter.completed
X-StoryProof-Signature: sha256=<HMAC-SHA256(secret, body)>

{
  "event": "manuscript.chapter.completed",
  "manuscript_id": 42,
  "external_id": "kakao-work-12345",
  "data": { "chapter_id": 101, "chapter_number": 1, "status": "COMPLETED" },
  "timestamp": "2026-07-10T03:12:45+00:00"
}
```

- 이벤트 종류: `manuscript.chapter.completed` / `manuscript.chapter.failed` /
  `analysis.consistency.completed` / `analysis.consistency.failed`
- **서명 검증 필수**: `HMAC-SHA256(secret, 요청 본문)`을 계산해
  `X-StoryProof-Signature` 값과 비교하세요 (위조 요청 차단).
- 전송 실패 시 최대 3회 재시도 (2s/4s 백오프). 최종 실패분은 상태 조회 API로 보완하세요.
- 조회: `GET /webhook` (secret 미노출) · 해제: `DELETE /webhook`

### 5. 사용량 조회 (무과금)

```http
GET /api/partner/v1/usage
→ { "partner_name": "카카오페이지", "plan": "pro", "monthly_quota": 100000,
    "used_this_month": 1523, "remaining": 98477 }
```

## 임베드 위젯 (뷰어/상세페이지용 챗봇)

파트너 사이트에 `<script>` 한 줄로 작품 Q&A 챗봇을 삽입할 수 있습니다.
**API 키는 절대 브라우저에 노출하지 마세요** — 대신 파트너 서버가 단기 세션 토큰을 발급합니다.

### 1. 세션 토큰 발급 (파트너 서버에서, 무과금)

```http
POST /api/partner/v1/widget-sessions
X-API-Key: <key>

{ "manuscript_id": 42, "chapter_id": 101, "ttl_minutes": 30 }
→ { "token": "eyJ...", "expires_in": 1800, "manuscript_id": 42, "chapter_id": 101 }
```

- `chapter_id`: 독자가 읽은 회차 — 토큰에 고정되어 위젯이 **이 회차까지만** 답변 (스포일러 방지, 클라이언트가 변경 불가)
- `ttl_minutes`: 1~1440분 (기본 30분). 독자 페이지 로드 시마다 발급 권장

### 2. 위젯 삽입 (파트너 페이지)

```html
<script src="https://<storyproof-host>/static/widget/storyproof-widget.js"
        data-token="<위 응답의 token>"
        data-title="달빛 조각사"
        data-color="#4F46E5"></script>
```

또는 프로그래매틱: `StoryProofWidget.init({ token, apiBase, title, color, position })`

- Shadow DOM으로 페이지 CSS와 완전 격리, 빌드 도구 불필요
- 위젯이 호출하는 `/api/widget/v1/qa`는 **질문당 1 unit** 과금 (파트너 귀속)
- 데모: `https://<storyproof-host>/static/widget/demo.html` 에 토큰 붙여넣기

## 파트너 등록 (StoryProof 관리자 전용)

```http
POST /api/v1/admin/partners
Authorization: Bearer <admin JWT>

{ "name": "카카오페이지", "contact_email": "partner@kakaopage.com",
  "plan": "pro", "monthly_quota": 100000, "rate_limit_per_minute": 300 }
```

응답에 최초 `api_key`가 포함됩니다 (재확인 불가 — 안전한 채널로 전달).
키 로테이션: `POST /api/v1/admin/partners/{id}/keys` → 신규 키 발급 후
`DELETE /api/v1/admin/partners/{id}/keys/{key_id}`로 구 키 폐기.

## 데이터 격리 원칙

- 파트너별 전용 서비스 계정으로 모든 데이터가 격리되며, 다른 파트너 또는
  일반 사용자의 데이터에는 어떤 경로로도 접근할 수 없습니다.
- 원문은 분석 목적 외 사용되지 않으며, 계약 종료 시 원문/벡터 전체 삭제를 지원합니다.
