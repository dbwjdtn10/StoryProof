# StoryProof 파트너 API — 성능 측정 결과 및 SLA 초안

> 측정일: 2026-07-10 · 도구: `scripts/loadtest/` (재현 방법은 문서 하단)

## 1. 측정 환경 및 범위

| 항목 | 값 |
|---|---|
| 서버 | uvicorn 단일 프로세스·단일 워커 (Windows 로컬) |
| DB | SQLite WAL (하네스용) — 프로덕션 PostgreSQL 대비 쓰기가 직렬화되어 **보수적(불리한) 수치** |
| LLM | **스텁 처리** — 아래 수치는 API 계층(인증·격리·계측·직렬화) 오버헤드만 측정 |
| 시나리오당 측정 | 15초, 워밍업 2초 별도 |

**중요**: Q&A 계열의 실제 사용자 체감 응답시간 = 아래 수치 + Gemini 생성 시간.
Gemini 2.5 Flash 기준 전형적으로 1~5초(비스트리밍), 스트리밍 첫 토큰 ~1초.
프로덕션 스택(Docker + PostgreSQL + 실제 LLM)에서의 재측정은 파일럿 전 필수.

## 2. 측정 결과 (에러율 전 시나리오 0%)

### 동시성 10

| 시나리오 | RPS | p50 | p95 | p99 |
|---|---|---|---|---|
| baseline (GET /) | 1,178 | 4ms | 9ms | 97ms |
| 사용량 조회 (GET /usage) | 341 | 27ms | 43ms | 75ms |
| 위젯 Q&A (POST /widget/v1/qa) | 282 | 8ms | 71ms | 661ms |
| 파트너 Q&A (POST /manuscripts/qa) | 159 | 49ms | 129ms | 240ms |
| 원고 접수 2회차 (POST /manuscripts) | 76 | 57ms | 505ms | 1,846ms |

### 동시성 50

| 시나리오 | RPS | p50 | p95 | p99 |
|---|---|---|---|---|
| baseline (GET /) | 914 | 38ms | 158ms | 244ms |
| 사용량 조회 | 171 | 233ms | 408ms | 2,213ms |
| 위젯 Q&A | 193 | 107ms | 564ms | 2,846ms |
| 파트너 Q&A | 83 | 511ms | 1,012ms | 2,428ms |
| 원고 접수 2회차 | 63 | 677ms | 1,898ms | 3,676ms |

해석: 단일 워커·SQLite 조건에서도 위젯 Q&A API 오버헤드는 약 200~280 RPS를
소화한다. 프로덕션에서는 PostgreSQL(동시 쓰기)과 uvicorn 다중 워커로 선형에
가깝게 확장 가능하며, Q&A 계열의 병목은 API 계층이 아니라 LLM 생성 시간이다.

## 3. 부하테스트로 발견·수정한 결함 (v1.0에 반영됨)

1. **Redis 장애 시 요청당 ~2초 페널티 → 전면 장애로 확산**
   - 레이트 리밋 검사가 요청마다 새 Redis 연결을 생성해, Redis 다운 시 매 요청이
     연결 타임아웃(~2초)을 지불 → 스레드풀 포화 → p50 20초, 동시성 50에서 에러율 100% 실측
   - 수정: 클라이언트 재사용 + **서킷 브레이커**(장애 감지 후 30초간 재시도 생략).
     수정 후 동일 조건에서 p50 27ms, 에러 0%. (`backend/core/partner_auth.py`)
2. **DB 커넥션 풀 기본값(pool 5 + overflow 10)은 동시성 50에서 고갈**
   - 풀 대기 30초 타임아웃으로 에러율 80~100% 실측
   - 운영 권장: `DB_POOL_SIZE=30`, `DB_MAX_OVERFLOW=20` 이상 (docker-compose에 반영됨)

## 4. SLA 초안 (파일럿 계약용)

| 지표 | Starter/Pro | Enterprise |
|---|---|---|
| 월 가용성 | 99.5% | 99.9% (협의) |
| 사용량/상태 조회 p95 | < 200ms | < 100ms |
| Q&A API 오버헤드 p95 (LLM 제외) | < 500ms | < 300ms |
| Q&A 체감 응답 p95 (LLM 포함) | < 8s (스트리밍 첫 토큰 < 2s) | < 5s |
| 원고 접수 접수응답(202) p95 | < 2s | < 1s |
| 회차 분석 처리 완료 | 접수 후 10분 내 (웹훅 통지) | 협의 |

※ 위 수치는 이번 측정을 근거로 한 **초안**이며, 프로덕션 스택 재측정 후 확정한다.

## 5. 재현 방법

```bash
# 터미널 1 — 하네스 서버 (LLM/Celery 스텁, SQLite)
python scripts/loadtest/server_harness.py 8123
# LLM 지연 시뮬레이션: LLM_STUB_DELAY_MS=1500 python scripts/loadtest/server_harness.py

# 터미널 2 — 부하 생성 (동시성 10/50 × 5개 시나리오, --quick 시 축소)
python scripts/loadtest/run_loadtest.py
# → scripts/loadtest/results.json + 콘솔 마크다운 테이블
```

프로덕션 측정 시: `docker compose up -d --build` 후 하네스 대신 실제 API에
동일한 `run_loadtest.py`를 사용하되 seed.json을 실제 파트너 키로 작성한다.
