# Tiptap 에디터 통합 기술 상세 문서

본 문서는 StoryProof 프로젝트에 적용된 Tiptap 리치 텍스트 에디터 및 커스텀 툴바의 작동 원리와 구조를 상세히 설명합니다.

---

## 1. 전체 구조 및 파일 역할

이번 작업은 주로 프론트엔드(`frontend/src`) 영역에서 이루어졌습니다. 주요 구성 요소는 다음과 같습니다.

### [NEW] NovelEditor.tsx (에디터 본체)
- **역할**: Tiptap의 코어 엔진을 설정하고 React 컴포넌트로 캡슐화합니다.
- **핵심 기술**:
  - `useEditor` 훅을 사용하여 에디터 인스턴스를 관리합니다.
  - **커스텀 및 확장 기능(Extensions)**:
    - `FontSize`, `LineHeight`: 텍스트 크기와 줄 간격 제어.
    - `TaskList`, `TaskItem`: 체크박스 목록 지원.
    - `Image`: URL 기반 사진 삽입 지원.
    - `Table`, `TableRow` 등: 표 삽입 및 구조 관리.
    - `Heading`: 레벨 1~4(제목 1~2, 개요 1~2) 지원.
  - `StarterKit`, `Underline`, `TextAlign`, `FontFamily` 등 필수 플러그인을 통합했습니다.

### [NEW] NovelToolbar.tsx (상단 제어 바)
- **역할**: 사용자에게 편집 도구를 제공하고, 클릭 시 에디터 명령을 실행합니다.
- **핵심 기술**:
  - `editor` 객체를 `props`로 전달받아 직접적으로 명령을 내립니다 (`editor.chain().focus()...run()`).
  - **Material Symbols**: Google Fonts 라이브러리를 통해 현대적인 아이콘 시스템을 적용했습니다.
  - **상태 연동**: `editor.isActive()`를 사용하여 현재 커서 위치의 서식 상태(Bold 여부 등)를 파악하고 버튼의 활성/비활성 스타일을 변경합니다.

### [MODIFY] ChapterDetail.tsx (통합 화면)
- **역할**: 소설 챕터 상세 화면에서 에디터와 툴바를 배치하고 데이터를 관리합니다.
- **핵심 기술**:
  - **멀티 에디터 제어**: 다중 장면(Scene) 구조이므로 각각의 장면에 `NovelEditor`가 존재합니다.
  - `setActiveEditor`: 어떤 에디터가 클릭(Focus)되었는지 추적하여, 상단의 단일 툴바가 현재 선택된 장면을 제어할 수 있도록 연결합니다.
  - **데이터 싱크**: `onUpdate` 콜백을 통해 에디터의 HTML 내용을 실시간으로 부모 컴포넌트의 `sceneTexts` 상태와 동기화합니다.

### [NEW] novel-toolbar.css (스타일링)
- **역할**: 툴바의 레이아웃과 에디터 내부 컨텐츠의 시각적 형식을 정의합니다.
- **주요 설정**:
  - `.ProseMirror`: Tiptap 에디터의 실제 입력 영역 스타일을 정의합니다 (여백, 폰트, 줄 간격 등).
  - 툴바 버튼의 `hover`, `active`, `disabled` 상태 디자인을 포함합니다.

---

## 2. 작동 원리 (Workflow)

### 2.1 텍스트 편집 과정
1. 사용자가 특정 장면(Scene)을 클릭하면 `NovelEditor`의 `onFocus`가 실행되어 `activeEditor` 상태가 업데이트됩니다.
2. 사용자가 툴바의 **'B' (굵게)** 버튼을 클릭합니다.
3. `NovelToolbar`는 `activeEditor.chain().focus().toggleBold().run()` 명령을 실행합니다.
4. Tiptap 엔진이 내부 DOM의 선택 영역을 `<strong>` 태그로 감싸거나 스타일을 변경합니다.
5. 변경된 결과는 `onUpdate`를 통해 HTML 문자열로 변환되어 `ChapterDetail`의 상태로 저장됩니다.

### 2.2 검색 기능
- 툴바의 검색창은 `window.find()` 브라우저 API를 사용하여 현재 문서 내에서 텍스트를 찾습니다. (향후 Tiptap 전용 검색 엔진으로 고도화 가능)

### 2.3 커스텀 스타일 (폰트 크기 및 간격)
- Tiptap의 `Extension.create`를 사용하여 새로운 명령어를 만들었습니다.
- 예를 들어 `setFontSize('24px')`가 실행되면, Tiptap은 텍스트 노드에 `<span style="font-size: 24px">`를 적용하도록 설계되었습니다.

---

## 3. 변경된 주요 코드 상세 (TSX/CSS 중심)

사용자께서 `.py` 파일 변경에 대해 물어보셨으나, 이번 작업은 100% **웹 UI 및 에디터 기능 강화**이므로 프론트엔드 파일 내부 로직 위주로 변경되었습니다.

- **`ChapterDetail.tsx`**:
  - `WritingToolbar` (기존) → `NovelToolbar` (신규)로 교체.
  - `dangerouslySetInnerHTML` 기반 수동 편집 → `NovelEditor` 컴포넌트 기반 관리로 체계화.
- **`index.html`**:
  - `<link rel="stylesheet" href="...">`를 추가하여 Google Material Symbols 폰트를 불러오도록 설정.

이 구조를 통해 향후 새로운 에디터 기능(예: 이미지 삽입, 표 만들기 등)을 추가할 때 `NovelEditor`의 `extensions` 배열에 플러그인만 추가하면 되는 확장성 높은 구조를 갖추게 되었습니다.
