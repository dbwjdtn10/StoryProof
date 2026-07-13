# 전용 인스턴스 / 멀티 리전 배포 런북 (Enterprise 플랜)

> 이 문서는 코드가 아니라 **운영 절차**입니다. StoryProof 앱 자체가 여러
> 리전에 스스로 배포되는 자동화 기능은 없습니다 — 대형 서점/플랫폼
> 파트너가 "우리 데이터를 다른 테넌트와 물리적으로 분리해 달라" 또는
> "특정 리전에 데이터를 둬야 한다(데이터 레지던시 요구사항)"고 요구할 때,
> Phase 1에서 만든 Docker 패키징(`Dockerfile` + `docker-compose.yml`)을
> 그대로 재사용해 **파트너 전용 스택을 통째로 하나 더 띄우는 방식**으로
> 대응합니다.

## 왜 이 방식인가

- 기존 아키텍처는 이미 "테넌트 격리 = 파트너별 서비스 계정(User) + 소유권
  필터링"으로 동작(Phase 1). 이는 **논리적 격리**이며 같은 DB/Pinecone
  인덱스를 공유한다.
- Enterprise 계약에서 요구하는 "전용 인스턴스"는 보통 **물리적 격리**
  (별도 DB, 별도 Pinecone 인덱스, 별도 서버/리전)를 의미한다.
- 새로운 멀티 리전 오케스트레이션 코드를 만드는 대신, 이미 검증된 단일
  스택 배포(Phase 1 Docker 패키징)를 파트너 수만큼 반복하는 것이 가장
  빠르고 실수가 적다 — "구현"이 아니라 "배포 반복"으로 해결.

## 절차

1. **인프라 준비**: 파트너가 요구하는 리전에 서버(또는 클라우드 인스턴스)
   준비. Docker/Docker Compose 설치.
2. **전용 `.env` 작성**: `.env.example`을 복사해 이 파트너만의 값으로 채움
   - `DATABASE_URL`/`POSTGRES_*`: 이 파트너 전용 Postgres (공유 DB 아님)
   - `PINECONE_INDEX_NAME`: 파트너 전용 인덱스 이름 (예: `<partner-slug>-index-384`)
   - `PINECONE_ENV`: 파트너가 요구하는 리전에 맞는 Pinecone 환경
   - `GOOGLE_API_KEY`: 별도 프로젝트/키 발급 권장 (사용량 분리, 장애 격리)
   - `SECRET_KEY`: 공유 스택과 다른 값 필수
3. **기동**: `docker compose up -d --build` (Phase 1에서 만든 그대로).
4. **파트너 등록**: 이 전용 스택의 `/api/v1/admin/partners`에 파트너를
   등록하되, `deployment_region`을 실제 리전 식별자로, `dedicated_instance_url`을
   이 스택의 공개 엔드포인트 URL로 지정 — 이는 운영 추적용 메타데이터이며,
   파트너에게 안내할 API 베이스 URL이 공유 스택과 달라짐을 의미한다.
5. **DNS/라우팅**: 파트너 전용 서브도메인(예: `partner-x.api.storyproof.com`)을
   이 스택으로 연결.
6. **모니터링/백업**: 공유 스택과 별도로 백업·모니터링 설정 (전용 계약이므로
   SLA도 별도 협의 대상, `docs/SLA.md` §4 Enterprise 행 참고).

## 한계 및 향후 과제

- 코드 배포(버전 업그레이드)는 스택마다 수동 반복 필요 — 파트너 수가
  늘어나면 CI/CD로 다중 스택 배포 자동화가 필요해짐 (아직 없음).
- 크로스 리전 장애 조치(failover)는 다루지 않음 — 각 전용 스택은 독립적.
- `Partner.deployment_region`/`dedicated_instance_url`은 현재 순수
  메타데이터 필드로, 파트너 API 요청을 실제로 다른 인스턴스로 라우팅하는
  로직은 없다 (전용 스택은 애초에 별도 URL로 직접 접근하므로 불필요).
