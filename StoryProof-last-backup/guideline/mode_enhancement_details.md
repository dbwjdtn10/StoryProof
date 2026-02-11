# StoryProof 모드별 기능 구현 상세 명세서

이 문서는 **StoryProof** 프로젝트의 **작가 모드(Writer Mode)**와 **독자 모드(Reader Mode)** 구현을 위해 수정 및 추가된 파일, 주요 기능, 사용된 라이브러리 및 로직을 상세히 기술합니다.

---

## 1. 공통 사항 (Common)

### 사용된 주요 라이브러리
- **@tiptap/react, @tiptap/starter-kit**: 리치 텍스트 에디터 및 뷰어 코어로 사용.
- **lucide-react**: 모던하고 일관된 UI 아이콘 (툴바, 사이드바 등) 사용.
- **react (hooks)**: `useState`, `useEffect`, `useRef` 등을 통한 상태 관리 및 DOM 제어.

### 공통 스타일링
- **CSS Variables**: 테마 및 사용자 설정(글꼴 크기 등)의 실시간 반영을 위해 CSS 변수 적극 활용.
- **Glassmorphism**: 최신 트렌드를 반영한 반투명 블러 효과(`backdrop-filter`)를 팝오버 및 플로팅 UI에 적용.

---

## 2. 작가 모드 (Writer Mode)
작가 모드는 창작에 집중할 수 있도록 직관적인 포맷팅 도구와 안정적인 에디팅 환경을 제공하는 데 중점을 두었습니다.

### 수정된 파일 및 위치
1.  **`frontend/src/components/NovelToolbar.tsx`**
    -   **역할**: 에디터 상단에 위치하여 텍스트 서식을 제어하는 툴바.
    -   **주요 변경 사항**:
        -   Tiptap 에디터 인스턴스(`editor`)를 prop으로 받아 명령을 실행하도록 구조화.
        -   `lucide-react` 아이콘을 사용하여 볼드, 이탤릭, 정렬, 리스트 등의 버튼 시각화.
        -   `sticky` 포지셔닝을 적용하여 스크롤 시에도 상단에 고정되도록 스타일링.
    -   **주요 로직**:
        ```typescript
        // 체이닝 방식을 통한 에디터 명령 실행
        <button onClick={() => editor.chain().focus().toggleBold().run()}>
            <Bold size={20} />
        </button>
        ```

2.  **`frontend/src/components/NovelEditor.tsx`**
    -   **역할**: 실제 텍스트가 입력되는 에디터 컴포넌트.
    -   **주요 변경 사항**:
        -   `EditorContent` 컴포넌트를 사용하여 Tiptap 에디터를 렌더링.
        -   각 장면(Scene)별로 독립적인 에디터 인스턴스를 가지거나, 통합된 에디터를 사용하는 구조 지원.
        -   **플레이스홀더 및 스타일**: 빈 줄에 안내 문구가 나오도록 CSS 커스터마이징.

3.  **`frontend/src/novel-toolbar.css`**
    -   **역할**: 툴바 및 에디터 관련 스타일 정의.
    -   **주요 내용**:
        -   `.ProseMirror`: 에디터 내부 컨텐츠의 기본 스타일(패딩, 아웃라인 제거 등) 정의.
        -   버튼 호버 효과 및 활성화(`active`) 상태 스타일링.

---

## 3. 독자 모드 (Reader Mode)
독자 모드는 사용자 경험(UX)을 최우선으로 하여, 읽기 편한 환경을 제공하고 개인화된 설정을 지원하도록 대대적인 리뉴얼을 진행했습니다.

### 신규 생성 및 수정된 파일

#### 1. `frontend/src/components/ReaderToolbar.tsx` (신규 생성)
-   **역할**: 독자 전용 프리미엄 툴바. 팝오버(Popover) UI를 통해 가독성 설정을 제공.
-   **주요 기능 및 로직**:
    -   **직관적인 아이콘**: `Type`(타이포그래피), `Font`(글꼴), `Palette`(테마), `Align`(간격), `Maximize`(너비) 아이콘 배치.
    -   **Popover UI 시스템**:
        -   `activePopover` 상태(`useState`)를 통해 현재 열린 설정창 관리.
        -   `useRef`와 `mousedown` 이벤트를 사용하여 **영역 밖 클릭 시 팝오버 닫기** 기능 구현.
    -   **설정 변경 핸들러**: 부모 컴포넌트(`ChapterDetail`)로부터 전달받은 `onSettingsChange` 함수를 통해 설정을 즉시 업데이트.

#### 2. `frontend/src/components/ChapterDetail.tsx` (대폭 수정)
-   **역할**: 챕터 뷰어 및 레이아웃을 담당하는 핵심 페이지 컴포넌트.
-   **주요 변경 사항**:
    -   **상태 관리 (`readerSettings`)**:
        -   글꼴 크기, 줄 간격, 문단 간격, 본문 너비, **폰트 종류(fontFamily)**, **테마(theme)**를 관리하는 객체 상태 추가.
        -   `localStorage`를 연동하여 새로고침 후에도 설정 유지.
    -   **CSS Variable 주입**:
        -   `useEffect`를 통해 `readerSettings`가 변경될 때마다 최상위 DOM 요소에 CSS 변수(`--reader-font-size`, `--reader-bg` 등)를 주입. 이를 통해 리렌더링 없이 즉각적인 스타일 반영.
    -   **편의 기능**:
        -   **진행률 표시줄(Progress Bar)**: 스크롤 위치를 계산하여 상단 바 너비 조절.
        -   **자동/수동 책갈피**: `localStorage`에 스크롤 위치 저장 및 복원.
        -   **독자 전용 툴바 통합**: 헤더 영역의 조건부 렌더링(`mode === 'reader'`)을 통해 `ReaderToolbar` 노출.

#### 3. `frontend/src/chapter-detail.css` (스타일 추가)
-   **역할**: 독자 모드 전용 스타일 및 테마 스타일링.
-   **주요 추가 내용**:
    -   **CSS Variables 활용**: 
        ```css
        .scenes-container {
            background-color: var(--reader-bg, #ffffff);
            color: var(--reader-text, #1a1a1a);
            transition: background-color 0.3s ease;
        }
        ```
    -   **프리미엄 팝오버 스타일**:
        -   `backdrop-filter: blur(16px)`: 뒤가 비치는 유리 효과.
        -   `box-shadow`: 깊이감을 주는 부드러운 그림자.
        -   `animation`: 팝오버 등장 시 부드럽게 떠오르는 `popover-fade-in` 애니메이션.

### 구현된 상세 기능 목록

1.  **타이포그래피 설정**:
    -   글자 크기 `12px` ~ `32px` 정밀 조절.
    -   전용 초기화 버튼 제공.
2.  **글꼴 변경 (Font Family)**:
    -   Noto Sans KR (기본), Noto Serif KR (명조), 나눔 명조, 나눔 고딕, Poppins, Inter 등 다양한 웹폰트 적용 지원.
3.  **테마 변경 (Theme)**:
    -   **라이트(Light)**: 기본 흰색 배경, 검은 텍스트.
    -   **세피아(Sepia)**: 눈이 편한 미색 배경(`#f4ecd8`), 갈색 텍스트.
    -   **다크(Dark)**: 어두운 배경(`#1a1a1a`), 밝은 회색 텍스트.
4.  **레이아웃 조절**:
    -   **줄 간격**: 표준(1.5), 넓음(2.0), 매우 넓음(2.5).
    -   **본문 너비**: 70% ~ 100% 반응형 조절.
5.  **상호작용 도구**:
    -   **수동 책갈피**: 현재 스크롤 위치 저장.
    -   **하이라이트/메모**: 텍스트 선택 후 강조 및 메모 저장 기능 (Tiptap API 활용).

---

이 문서는 프로젝트의 현재 상태를 기준으로 작성되었으며, 추후 기능 추가에 따라 업데이트될 수 있습니다.
