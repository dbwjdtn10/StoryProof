# StoryProof 프론트엔드 폴더 상세 비교 분석 (last-backup vs aa)

`StoryProof-last-backup/frontend`와 `StoryProof-aa/frontend` 폴더를 파일 하나하나 수준에서 상세히 비교한 결과입니다. **last-backup** 버전은 실제 상용 서비스 수준의 UI/UX 완성도를 목표로 하며, **aa** 버전은 핵심 기능의 프로토타이핑과 실험에 집중되어 있습니다.

---

## 1. 프로젝트 설정 및 루트 파일 (Root & Config)

| 파일명 | last-backup (최신 버전) | aa (실험 버전) | 차이점 및 특징 |
| :--- | :--- | :--- | :--- |
| `package.json` | **Tiptap(16개 이상 패키지)**, **MUI**, **Shadcn** 등 대량의 UI 라이브러리 포함 | 기본 Radix UI와 Lucide 아이콘 위주 | `last-backup`은 리치 텍스트 편집과 정교한 디자인 시스템을 위한 의존성이 압도적으로 많음. |
| `vite.config.ts` | 고정된 Vite 버전(6.3.5) 사용 | 최신 버전(6.4.1) 사용 | 빌드 안정성을 위해 `last-backup`에서 특정 버전을 고정함. |
| `index.html` | 동일한 기본 구조 | 동일한 기본 구조 | 제목과 메타데이터는 대동소이함. |

---

## 2. API 레이어 (`src/api/`)

| 파일명 | last-backup | aa | 차이점 및 특징 |
| :--- | :--- | :--- | :--- |
| `novel.ts` | 챕터 상세, 바이블 데이터, 재분석 등 핵심 로직 포함 | 동일하나 일부 타입 정의가 단순함 | `last-backup`의 API는 에디터 연동을 위한 메타데이터 처리가 더 정교함. |
| `auth.ts` | 로그인, 회원가입, 내 정보 조회(`me`) 포함 | 로그인, 회원가입 중심 | `last-backup`은 사용자 설정을 위한 `me` API 연동이 강화됨. |
| `chat.ts` | 동적 모델 선택(`model`) 파라미터 지원 | 기본 챗 요청 | `last-backup`은 설정 메뉴에서 선택한 모델을 API에 반영함. |
| `prediction.ts` | (삭제되거나 `novel.ts`로 통합됨) | 별도 파일로 존재 | `aa`에서는 스토리 예측이 핵심 실험이었으나, `last-backup`에서는 안정적인 기능 위주로 재편됨. |

---

## 3. 핵심 컴포넌트 (`src/components/`)

### 3.1 에디터 패러다임의 변화
- **`ChapterDetail.tsx` (가장 큰 차이점)**:
    - **last-backup**: **Tiptap 리치 텍스트 에디터**를 탑재. 글자 크기, 줄 간격, 배경 테마(세피아, 다크 모드 등)를 사용자가 직접 조절 가능(`readerSettings`). 또한 북마크와 스크롤 위치 저장 기능이 정교함.
    - **aa**: 단순 **Textarea** 또는 씬(Scene) 단위의 텍스트 블록 기반. 서식 지정을 할 수 없으며 단순 텍스트 입력만 가능.

### 3.2 신규 및 삭제 파일
- **`NovelEditor.tsx`, `NovelToolbar.tsx`, `WritingToolbar.tsx`, `ReaderToolbar.tsx`**:
    - `last-backup`에만 존재하는 파일들입니다. 작가와 독자에게 각각 최적화된 도구바를 제공하기 위한 모듈화된 구조입니다.
- **`SettingsModal.tsx`**:
    - `last-backup`에서 오늘 추가된 핵심 파일. 닉네임 확인, 로그아웃, **LLM 모델(2.0, 2.5 등) 변경** 기능을 제공합니다.
- **`Dashboard.tsx`**:
    - `last-backup`에만 존재. 소설 목록과 최근 작업 챕터를 한눈에 보는 관리 화면입니다.
- **`ui/` 폴더**:
    - `last-backup`에만 존재하며 **48개**의 Shadcn/UI 컴포넌트(Button, Card, Input 등)가 들어있습니다. `aa`에서는 일일이 CSS로 만들던 UI를 여기서는 표준화된 컴포넌트로 사용합니다.

### 3.3 챗봇 시스템
- **`CharacterChat/` (last-backup)**: 폴더 구조로 분리되어 방 만들기, 채팅방 목록 등 **멀티룸 챗 시스템**으로 발전함.
- **`CharacterChatBot.tsx` (aa)**: 하나의 파일에 모든 로직이 들어있는 프로토타입 형태.

---

## 4. 스타일링 및 테마 시스템

- **last-backup**: 
    - **Tailwind CSS**와 **CSS 변수**(`--reader-font-size` 등)를 적극 활용하여 런타임에 테마(배경색, 글자색)를 즉각 변경할 수 있는 유연성을 갖춤.
    - `novel-toolbar.css` 등 컴포넌트별 스타일이 잘 정돈됨.
- **aa**: 
    - `login.css`, `upload.css`, `chatbot.css`, `theme.css` 등 원시적인 형태의 CSS 파일이 파편화되어 있음. 유지보수가 어렵고 확장성이 부족함.

---

## 종합 결론

1.  **StoryProof-last-backup**은 **"플랫폼"**입니다. 작가가 실제 글을 쓰기 좋은 환경(리치 에디터)과 독자가 읽기 좋은 환경(독서 설정)을 모두 갖추었으며, 코드 구조 역시 표준화된 UI 라이브러리를 사용하여 유지보수가 용이합니다.
2.  **StoryProof-aa**는 **"실험실"**입니다. 특정 AI 기능(스토리 예측 등)을 테스트하기 위한 최소한의 UI만 갖추고 있으며, 텍스트 처리 자체의 성능이나 로직 검증에 중점을 두고 있습니다.

**결론적으로, 현재 개발 중인 최신 UI와 모든 편의 기능은 `last-backup`에 집약되어 있습니다.**
