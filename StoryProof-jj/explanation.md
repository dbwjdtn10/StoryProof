# StoryProof-jj: 통합 설정 오류 검사 시스템

이 프로젝트는 `StoryProof-RR`의 글로벌 맥락 파악 기능과 `StoryProof-hong`의 세부 설정 검색 기능을 하나로 합쳐 더욱 강력해진 소설 설정 검수 시스템입니다.

## 🔗 주요 통합 내용

### 1. 하이브리드 컨텍스트 구성
기존의 두 파일이 가진 장점을 하나로 통합했습니다:
- **글로벌 스토리보드 (`StoryProof-RR` 방식)**: 소설의 모든 씬(Scene) 요약본을 순서대로 LLM에 전달하여, 현재 문장이 소설의 전체 흐름에서 벗어나지 않는지 확인합니다.
- **세부 설정 벡터 검색 (`StoryProof-hong` 방식)**: Pinecone 벡터 DB를 사용하여 현재 문장과 관련된 특정 캐릭터 설정, 고유 명사 정의 등 구체적인 정보를 찾아 LLM에 전달합니다.

### 2. 고도화된 프롬프트 엔진
`backend/services/analysis/consistency_checker.py`에 구현된 통합 엔진은 다음과 같이 작동합니다:
- **시스템 지침**: 소설 전문 편집자의 페르소나를 부여하고, 설정 충돌(⚠️), 개연성(⚙️), 보이스 불일치(🗣️)의 세 가지 명확한 기준을 제시합니다.
- **Chain-of-Thought**: LLM이 단계별로 사고하여 단순한 오류 탐지를 넘어 구체적인 수정 대안까지 제시하도록 설계되었습니다.
- **JSON 응답 최적화**: Gemini 1.5/2.0 Flash의 `response_mime_type: "application/json"` 기능을 활용하여 정확한 구조의 분석 결과를 보장합니다.

## 📂 파일 구조
- `backend/services/analysis/consistency_checker.py`: 통합 검사 로직의 핵심 파일입니다.
- `backend/core/config.py`: Gemini 및 Pinecone API 설정이 포함되어 있습니다.
- `backend/db/`: 소설 및 씬 정보를 관리하는 데이터베이스 레이어입니다.
- `.env`: 프로젝트 실행을 위한 환경 변수 파일입니다 (새로 생성됨).

## 🚀 사용법 및 문제 해결
1. `StoryProof-jj` 폴더로 이동합니다.
2. `pip install -r requirements.txt`를 실행하여 필요한 패키지(Celery 등)를 설치합니다.
3. `.env` 파일에 `GOOGLE_API_KEY`와 `PINECONE_API_KEY`를 설정합니다. (DB 설정은 이미 기본적으로 구성되어 있습니다.)
4. `python -m uvicorn backend.main:app --reload`를 실행하여 서버를 시작합니다.

### 💡 주요 패치 내역 (Windows 대응)
- **Celery 의존성 해결**: 프로젝트 실행에 필요한 `celery` 및 `redis` 패키지를 `requirements.txt`에 맞춰 설치 완료했습니다.
- **인코딩 오류 수정**: Windows 환경에서 로그 출력 시 발생하던 Unicode 인코딩 오류(`✓` 문자 등)를 안전한 ASCII 문자로 대체하여 해결했습니다.
- **실행 경로 안정화**: 일부 Windows 환경에서 `uvicorn`을 직접 실행할 경우 패키지 인식 오류가 발생할 수 있어, `python -m uvicorn` 형식을 권장하도록 가이드를 업데이트했습니다.

---
이 시스템은 단순한 오타 교정을 넘어, 작가가 설정한 '바이블'과 소설의 '역사'를 모두 기억하는 인공지능 편집자로서 작동합니다.
