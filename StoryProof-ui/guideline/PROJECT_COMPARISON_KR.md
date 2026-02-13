# StoryProof 프로젝트 버전 비교 분석 (StoryProof-aa vs StoryProof-last-backup)

두 프로젝트의 차이점을 분석한 결과, **StoryProof-last-backup**은 사용자 편의성과 서비스 완성도에 초점을 맞춘 최신 웹 애플리케이션 버전인 반면, **StoryProof-aa**는 로컬 AI 및 NLP 연구/실험에 더 집중된 버전으로 보입니다.

## 1. 주요 기능 차이

| 기능 | StoryProof-last-backup | StoryProof-aa |
| :--- | :--- | :--- |
| **에디터 (Editor)** | **Tiptap 기반 리치 텍스트 에디터**<br>(제목, 글꼴, 표, 이미지 등 지원) | **기본 텍스트 에디터**<br>(주로 텍스트 위주의 단순 편집) |
| **로컬 저장** | **지원** (.txt 파일 다운로드 기능) | 미지원 |
| **설정 메뉴** | **지원** (사용자 정보, 로그아웃, 모델 선택) | 미지원 |
| **동적 모델 변경** | **지원** (Gemini 2.0/2.5/1.5 Pro 등 선택 가능) | 미지원 (기본 설정 모델 사용) |
| **사용자 인터페이스** | **고도화된 UI** (Shadcn/UI 기반, Dashboard 포함) | 기본 UI (핵심 기능 위주 구성) |

## 2. 기술 스택 및 라이브러리 차이

### StoryProof-last-backup (웹 서비스 최적화)
- **Frontend**: `NovelEditor`, `WritingToolbar`, `SettingsModal` 등 풍부한 컴포넌트 라이브러리 및 UI 세트 사용.
- **Backend**: 클라우드 AI(Google Gemini) 연동에 최적화되어 있으며, 서비스 로직이 분리되어 있음.
- **문서화**: 아키텍처 설명서(`ARCHITECTURE_KR.md`), 데이터베이스 가이드 등 상세 문서 포함.

### StoryProof-aa (AI 연구/NLP 실험)
- **NLP 집중**: `torch`, `transformers`, `kiwipiepy`(한국어 형태소 분석), `rank_bm25` 등 무거운 로집 AI/검색 라이브러리 포함.
- **검색 알고리즘**: 로컬 환경에서의 고급 검색 및 형태소 분석 실험을 위한 의존성이 더 많음.
- **가벼운 구조**: 웹 기능보다는 백엔드의 분석 로직 및 데이터 처리에 더 집중된 구조.

## 3. 파일 구조 차이

- **StoryProof-last-backup**:
  - `redis/`: Redis 설정 폴더 포함.
  - `SettingsModal.tsx`, `NovelEditor.tsx`: 최신 추가된 핵심 UI 파일.
  - 각종 프로젝트 가이드 문서(`ARCHITECTURE_KR.md` 등) 다수.
- **StoryProof-aa**:
  - `_verify.py`: 기능 검증용 스크립트 존재.
  - `requirements.txt`: 약 200MB 이상의 머신러닝 라이브러리 의존성 포함.

## 결론
- **StoryProof-last-backup**은 실제 사용자가 편리하게 소설을 집필하고 관리할 수 있도록 **UI/UX가 크게 발전된 버전**입니다. 특히 오늘 작업한 **로컬 저장 및 모델 변경 설정** 기능이 반영되어 있어 실제 사용에 가장 적합합니다.
- **StoryProof-aa**는 백엔드에서의 **고급 텍스트 분석 알고리즘이나 로컬 모델 실행**을 테스트하기 위한 용도로 사용하기 좋습니다.
