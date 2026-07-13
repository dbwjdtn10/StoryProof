# StoryProof 사업화 발전방향 (Business Roadmap)

> 작성일: 2026-07-10
> 목표: StoryProof를 ① 자체 웹서비스(B2C SaaS)와 ② 인터넷서점/웹소설 플랫폼 대상 B2B API 상품으로 발전

---

## 1. 현재 자산 진단

| 자산 | 상태 | 상품성 |
|------|------|--------|
| RAG 기반 작품 Q&A (하이브리드 검색 + 스포일러 방지용 회차 필터) | 구현 완료 | ★★★ 핵심 판매 포인트 |
| 설정 일관성 검증 (플롯 모순/캐릭터 충돌 탐지) | 구현 완료 | ★★★ 편집자/작가 도구로 독보적 |
| 캐릭터 페르소나 챗봇 | 구현 완료 | ★★★ 독자 인게이지먼트 상품 |
| 스토리 예측, 회차 분석(플롯/문체/종합) | 구현 완료 | ★★ 작가 보조 도구 |
| 이미지 생성 (Imagen) | 구현 완료 | ★★ 표지/삽화 초안용 |
| 작가용 에디터 (TipTap) + 파일 임포트/익스포트 | 구현 완료 | ★★ B2C 리텐션 요소 |

**핵심 인사이트**: 교보문고·알라딘·카카오페이지가 사려는 것은 이 프로젝트의 **UI가 아니라 기능(API)**이다.
그들은 이미 자체 뷰어/스토어를 갖고 있으므로, 판매 상품은 "그들의 작품 데이터를 넣으면
Q&A·일관성 검증·캐릭터 챗봇이 나오는 API"가 되어야 한다.

---

## 2. 타깃별 상품 정의

### A. 웹소설 플랫폼 (카카오페이지, 네이버시리즈, 문피아, 조아라)
- **독자용 "작품 챗봇"**: 뷰어에 임베드. "지난 화까지 무슨 일이 있었지?" 회차 필터로 스포일러 차단 → `POST /manuscripts/{id}/qa` (chapter_id 파라미터)
- **캐릭터 챗봇**: 인기작 캐릭터와 대화 → 팬덤 인게이지먼트/체류시간 증가
- **연재 검수 자동화**: 신규 회차 업로드 시 설정 붕괴 자동 탐지 → 작가 스튜디오 기능으로 제공
- 과금 모델: 월 구독(작품 수 기반) + 호출량 종량제

### B. 인터넷서점 (교보문고, 알라딘, 예스24)
- **eBook 리더 내 "책에게 묻기"**: 구매한 책 내용 기반 Q&A
- **AI 작품 요약/미리보기**: 상세페이지용 자동 생성 콘텐츠
- 과금 모델: 타이틀당 인덱싱 비용 + 호출량 종량제

### C. 자체 웹서비스 (B2C SaaS)
- 타깃: 웹소설 작가 지망생/기성 작가 (연재 관리 + AI 검수 + 독자 반응 시뮬레이션)
- 프리미엄 모델: 무료(월 N회 분석) / 프로(무제한 분석 + 이미지 생성) 
- 역할: B2B 영업을 위한 **쇼케이스** — "데모를 직접 써보세요"

---

## 3. 단계별 로드맵

### Phase 1 — 상품화 기반 (✅ 이번 작업으로 완료)
- [x] **B2B 파트너 API 계층** (`/api/partner/v1/*`)
  - API 키 인증 (X-API-Key, SHA-256 해시 저장)
  - 테넌트 격리 (파트너별 서비스 계정으로 데이터 분리)
  - 사용량 계측 (`api_usage_logs` — 과금/정산 근거)
  - 월간 쿼터 + 분당 레이트 리밋 (플랜별 차등)
  - 원고 접수 → 상태 폴링 → Q&A / 일관성 검증 워크플로
- [x] **파트너 관리 API** (관리자 전용: 파트너 등록, 키 발급/폐기, 사용량 집계)
- [x] **배포 패키징**: Dockerfile + docker-compose (한 명령으로 전체 스택 기동)
- [x] **보안 하드닝**: 챗봇 엔드포인트 인증 추가, 분석 요청 소유권 검증, 프로덕션 SECRET_KEY 가드

### Phase 2 — 파일럿 준비 (진행 중)
- [x] **웹훅 콜백**: 원고 처리/분석 완료 시 파트너 URL로 통지 (HMAC-SHA256 서명, 3회 재시도) — `PUT /api/partner/v1/webhook`
- [x] **EPUB 임포트**: spine 단위 자동 회차 분리 (`POST /manuscripts/upload`), B2C 업로드에도 .epub 지원
- [x] **Alembic 마이그레이션 정식화**: 파트너 테이블 리비전 추가 (`a1c9d47b8e02`), 단일 head 확인
- [x] **임베드 위젯 SDK**: `<script>` 한 줄 연동 JS 챗봇 위젯 (`/static/widget/storyproof-widget.js`)
      — 파트너 서버가 `POST /widget-sessions`로 단기 세션 토큰 발급(API 키 브라우저 미노출),
      토큰에 작품/회차 범위 고정(스포일러 방지), Shadow DOM 격리, 데모 페이지 포함
- [x] **관리 대시보드**: 파트너 등록/키 발급·폐기/월간 사용량(쿼터 대비) 시각화 —
      관리자 계정 로그인 시 업로드 화면 좌하단 "파트너 관리" 버튼으로 진입
- [x] **부하 테스트 + SLA 문서**: API 계층 실측 완료 → [docs/SLA.md](SLA.md)
      (위젯 Q&A 오버헤드 ~280 RPS/p95 71ms @c=10, 에러 0%. Redis 장애 시 전면 마비
      결함과 DB 풀 고갈 결함을 발견·수정.) 프로덕션 스택(Docker+PostgreSQL+실LLM)
      재측정도 2026-07-13 quick 모드(동시성 10)로 완료 — Q&A 체감 p95 1.1~2.4초,
      에러 0%, SLA 초안 목표(<8s) 충족. 동시성 50 실측은 비용 부담으로 파일럿
      계약 확정 후 진행 예정.

### Phase 3 — 스케일 (파일럿 계약 후)
- [x] **검색 품질 개선 — 코드 수정** (E2E 데모에서 발견, 2026-07-11 / 수정 2026-07-13):
  - 회차 수가 적은 작품은 BM25 성분이 0에 수렴 → 하이브리드 점수가 답변 게이트
    (0.55)를 구조적으로 못 넘어 전부 "찾을 수 없음" 처리됨. **수정**: 코퍼스
    크기(`SEARCH_MIN_BM25_CORPUS_SIZE`, 기본 5) 미만이거나 BM25 신호가 전혀
    없으면 dense_weight를 1.0으로 보정 (`embedding_engine.py::search`)
  - e5 계열 임베딩을 `query:`/`passage:` 프리픽스 없이 사용 중 → 코사인 유사도가
    본래보다 낮게 나옴. **수정**: `embed_text`/`embed_texts_batch`에 프리픽스
    추가. 회귀 테스트 6건 추가(`backend/tests/test_embedding_search.py`)
  - [ ] **잔여 작업**: 프리픽스 변경으로 기존 Pinecone 인덱스(프리픽스 없이
    임베딩됨)와 새 쿼리(프리픽스 있음) 간 분포가 어긋나므로 **전체 재인덱싱
    필요** — 아직 미실행. 검색 품질 평가셋(질문-정답 쌍)도 아직 없음
- [x] **LLM 비용 최적화** (2026-07-13):
  - **캐싱 고도화**: 콘텐츠 SHA-256 해시 기반 캐시 히트 스킵을 3개 경로에
    추가 — 스토리보드 재분석(`NovelService.analyze_chapter`, 내용 불변 시
    Celery 큐잉 자체를 생략), 회차 분석(`analyze_chapter_task`, plot/style/
    overall), 설정 일관성 검사(`detect_inconsistency_task`). 기존 API
    응답 계약(task_id/폴링) 변경 없이 태스크 내부에서 LLM 호출만 생략
  - **배치 처리**: 씬 구조화를 `SCENE_STRUCTURE_BATCH_SIZE`(기본 3)개씩
    묶어 한 번의 LLM 호출로 처리(`structure_scenes_batch`). 배치 응답
    파싱 실패/개수 불일치 시 해당 배치만 씬별 개별 호출로 자동 폴백.
    실 Gemini API로 2씬 배치 품질 검증 완료(씬 간 캐릭터/이벤트 혼선 없음)
  - **모델 티어링**: 최종 답변 품질에 영향이 적은 보조 판단(검색 공백
    탐지, `_identify_search_gaps`)을 `GEMINI_LITE_MODEL`(gemini-2.5-flash-lite)로 하향
  - Alembic 마이그레이션(`d3f6a91c5b47`, Chapter/Analysis에 content_hash
    컬럼 추가), 회귀 테스트 10건(`test_llm_caching.py`,
    `test_scene_batch_structuring.py`)
- [x] **멀티 리전/전용 인스턴스 옵션** (2026-07-13): 이 항목은 애플리케이션
  코드가 아니라 배포 절차 문제라, `Partner.deployment_region`/
  `dedicated_instance_url` 메타데이터 필드만 추가(관리자 API로 등록·조회
  가능)하고, 실제 격리 배포는 Phase 1 Docker 패키징을 재사용하는 런북으로
  대응 — `docs/DEDICATED_DEPLOYMENT.md` 참고. 앱이 스스로 여러 리전에
  자동 배포/라우팅하지는 않음(전용 스택은 별도 URL로 직접 접근).
  Alembic 마이그레이션(`7f4d9a2e6c31`), 회귀 테스트 1건 추가
- [x] **콘텐츠 보안 계약 대응** (2026-07-13): `Partner.content_retention_mode`
  (`"full"`/`"minimal"`, 파트너 등록 시 지정). `"minimal"`이면 원고 회차
  인덱싱 완료 즉시 `Chapter.content`(원문 전체)를 삭제하고 Pinecone
  벡터+`VectorDocument.chunk_text`(청크 단위)만 보관. Q&A/일관성 검사는
  계속 동작(일관성 검사는 원문 저장이 아닌 매 요청 전송 텍스트 기반이라
  영향 없음), 원문이 필요한 재분석·plot/style 분석만 이후 불가능해짐 —
  트레이드오프를 `docs/PARTNER_API.md`에 명시. Alembic 마이그레이션
  (`e7b2c19f4a08`), 회귀 테스트 4건(`test_content_retention.py`)
- [x] **정산 자동화** (2026-07-13): `api_usage_logs`를 연월별로 집계해
  `Invoice` 레코드 생성(`backend/services/billing_service.py`). 관리자
  API(`POST/GET /api/v1/admin/partners/{id}/invoices`)로 수동 생성·조회
  가능, Celery Beat(`generate_monthly_invoices_task`)가 매월 1일 00:10
  (Asia/Seoul)에 전체 활성 파트너 지난달 인보이스를 자동 생성(docker-compose
  `beat` 서비스 추가). 동일 연월 재생성 시 갱신(중복 없음). **단가는
  미확정** — `BILLING_PLAN_PRICING`(config.py)은 임시값이며 실제 계약
  단가로 교체 필요(§5 참고). enterprise는 개별 계약 전제로 자동 계산 제외.
  Alembic 마이그레이션(`c5a08e3f1b92`), 회귀 테스트 5건(`test_billing_service.py`)
- [x] **ISMS/개인정보 처리 방침 등 컴플라이언스 문서** (2026-07-13):
  `docs/PRIVACY_POLICY.md`(개인정보 처리방침 초안), `docs/ISMS_READINESS.md`
  (ISMS-P 갭 분석 — 이미 구현된 기술 통제 vs 부족한 부분 체크리스트).
  **법률 자문 검토 전까지는 초안이며, 실제 게시/인증 취득에는 별도 절차
  필요** — 두 문서 모두 상단에 명시. 회사 등록번호/DPO 연락처 등 사업자가
  채워야 할 항목은 `[ ]`로 표시.
- [x] **코드 정리** (2026-07-13): B2B 상용화 작업(Phase 1~3) 전체 diff를
  훑어 죽은 코드 제거 — `backend/services/analysis/agent.py`(호출자 없는
  `StoryConsistencyAgent` 중복 구현체, 파일 전체 삭제), `chatbot_service.py`의
  `_generate_multi_queries`/`_trim_cache`(호출자 없던 미사용 캐시 서브시스템
  전체), `gemini_structurer.py`의 `_extract_global_entities_batched`(호출자
  없던 구버전 배치 로직, 이번에 새로 만든 `structure_scenes_batch`와 이름이
  비슷해 혼동 소지가 있었음). `worker/tasks.py`의 중복된 "# 6. 처리 완료"
  주석과 리팩터링 메모 잔재 주석 정리. 전체 테스트(47건) 및 앱 임포트
  체인 정상 확인 후 커밋.

---

## 4. 영업 시나리오 (파트너 데모 흐름)

```
1. 관리자: POST /api/v1/admin/partners        → 파트너 등록 + API 키 발급
2. 파트너: POST /api/partner/v1/manuscripts   → 작품 원고 접수 (회차 배열)
3. 파트너: GET  /api/partner/v1/manuscripts/{id}/status  → ready: true 확인
4. 파트너: POST /api/partner/v1/manuscripts/{id}/qa      → 독자 질문에 즉시 답변
5. 파트너: POST /api/partner/v1/manuscripts/{id}/consistency → 신규 회차 검수
6. 파트너: GET  /api/partner/v1/usage         → 사용량/잔여 쿼터 투명 확인
```

데모 스크립트: `docs/PARTNER_API.md` 참고.

## 5. 가격 구조 초안

| 플랜 | 월 기본료 | 포함 호출 | 초과 과금 | 대상 |
|------|-----------|-----------|-----------|------|
| Starter | 무료~소액 | 10,000 units | 종량제 | 파일럿/PoC |
| Pro | 중간 | 100,000 units | 할인 종량제 | 중형 플랫폼 |
| Enterprise | 협의 | 무제한/전용 | 계약 | 대형 서점/플랫폼 |

unit 정의: 원고 접수=회차당 1, Q&A=질문당 1, 일관성 검증=건당 1 (상태 조회/사용량 조회는 무과금).
