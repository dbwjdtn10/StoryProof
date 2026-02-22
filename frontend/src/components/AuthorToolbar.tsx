import React from 'react';
import { Editor } from '@tiptap/react';
import { Settings } from 'lucide-react';

interface AuthorToolbarProps {
    editor: Editor | null;
    onOpenSettings: () => void;
}

export const AuthorToolbar = ({ editor, onOpenSettings }: AuthorToolbarProps) => {
    const [, forceUpdate] = React.useReducer((x) => x + 1, 0);

    React.useEffect(() => {
        if (!editor) return;

        const updateHandler = () => forceUpdate();
        editor.on('transaction', updateHandler);
        editor.on('selectionUpdate', updateHandler);

        return () => {
            editor.off('transaction', updateHandler);
            editor.off('selectionUpdate', updateHandler);
        };
    }, [editor]);

    const [searchValue, setSearchValue] = React.useState('');
    const searchIndexRef = React.useRef(0); // 다음 검색 시작 위치

    const handleSearch = () => {
        if (!searchValue || !editor) return;

        const { doc } = editor.state;
        const query = searchValue.toLowerCase();
        const startFrom = searchIndexRef.current;
        let matchFrom = -1;
        let matchTo = -1;

        // 전체 텍스트에서 위치 찾기
        doc.descendants((node, pos) => {
            if (matchFrom >= 0) return false;
            if (!node.isText || !node.text) return;

            const text = node.text.toLowerCase();
            if (pos + node.nodeSize <= startFrom) return;

            const offset = Math.max(0, startFrom - pos);
            const idx = text.indexOf(query, offset);
            if (idx !== -1) {
                matchFrom = pos + idx;
                matchTo = matchFrom + searchValue.length;
                return false;
            }
        });

        if (matchFrom >= 0) {
            // 선택 + Tiptap 내장 스크롤
            editor.chain().setTextSelection({ from: matchFrom, to: matchTo }).scrollIntoView().run();
            searchIndexRef.current = matchTo;
        } else if (startFrom > 0) {
            // 끝까지 못 찾으면 처음부터 다시
            searchIndexRef.current = 0;
            handleSearch();
        }
    };

    // 검색어 변경 시 위치 초기화
    React.useEffect(() => {
        searchIndexRef.current = 0;
    }, [searchValue]);

    return (
        <div className="novel-toolbar author-toolbar">
            {/* 1. Undo/Redo */}
            <div className="group">
                <button
                    onClick={() => editor?.chain().focus().undo().run()}
                    disabled={!editor?.can().undo()}
                    title="되돌리기"
                >
                    <span className="material-symbols-outlined">undo</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().redo().run()}
                    disabled={!editor?.can().redo()}
                    title="다시 실행"
                >
                    <span className="material-symbols-outlined">redo</span>
                </button>
            </div>

            <div className="separator" />

            {/* 2. Style Select */}
            <select
                onChange={(e) => {
                    if (!editor) return;
                    const val = e.target.value;
                    if (val === 'p') editor.chain().focus().setParagraph().run();
                    else editor.chain().focus().toggleHeading({ level: parseInt(val) as any }).run();
                }}
                value={
                    editor?.isActive('heading', { level: 1 }) ? '1' :
                        editor?.isActive('heading', { level: 2 }) ? '2' :
                            editor?.isActive('heading', { level: 3 }) ? '3' :
                                editor?.isActive('heading', { level: 4 }) ? '4' : 'p'
                }
                disabled={!editor}
                className="style-select"
            >
                <option value="p">바탕글</option>
                <option value="1">제목 1</option>
                <option value="2">제목 2</option>
                <option value="3">개요 1</option>
                <option value="4">개요 2</option>
            </select>

            <div className="separator" />

            {/* 3. Font Family */}
            <select
                onChange={(e) => {
                    if (!editor) return;
                    editor.chain().focus().setFontFamily(e.target.value).run();
                }}
                value={editor?.getAttributes('textStyle').fontFamily || ''}
                disabled={!editor}
                className="font-select"
            >
                <option value="">글꼴 선택</option>
                <option value="Inter">Inter</option>
                <option value="Roboto">Roboto</option>
                <option value="Pretendard">Pretendard</option>
                <option value="Nanum Myeongjo">나눔명조</option>
                <option value="serif">Serif</option>
                <option value="monospace">Monospace</option>
            </select>

            {/* 4. Font Size */}
            <select
                onChange={(e) => {
                    if (!editor) return;
                    (editor.chain().focus() as any).setFontSize(e.target.value).run();
                }}
                value={editor?.getAttributes('textStyle').fontSize || '16px'}
                disabled={!editor}
                className="size-select"
            >
                {[12, 14, 16, 18, 20, 24, 30, 36].map(size => (
                    <option key={size} value={`${size}px`}>{size}px</option>
                ))}
            </select>

            <div className="separator" />

            {/* 5. Character Formatting */}
            <div className="group">
                <button
                    onClick={() => editor?.chain().focus().toggleBold().run()}
                    className={editor?.isActive('bold') ? 'is-active' : ''}
                    title="굵게"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_bold</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().toggleItalic().run()}
                    className={editor?.isActive('italic') ? 'is-active' : ''}
                    title="기울임"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_italic</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().toggleUnderline().run()}
                    className={editor?.isActive('underline') ? 'is-active' : ''}
                    title="밑줄"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_underlined</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().toggleStrike().run()}
                    className={editor?.isActive('strike') ? 'is-active' : ''}
                    title="취소선"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_strikethrough</span>
                </button>
                <div className="color-picker-wrapper" title="글자 색상">
                    <span className="material-symbols-outlined">format_color_text</span>
                    <input
                        type="color"
                        onChange={e => editor?.chain().focus().setColor(e.target.value).run()}
                        value={editor?.getAttributes('textStyle').color || 'var(--foreground)'}
                        disabled={!editor}
                    />
                </div>
            </div>

            <div className="separator" />

            {/* 6. Alignment */}
            <div className="group">
                <button
                    onClick={() => editor?.chain().focus().setTextAlign('left').run()}
                    className={editor?.isActive({ textAlign: 'left' }) ? 'is-active' : ''}
                    title="왼쪽 정렬"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_align_left</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().setTextAlign('center').run()}
                    className={editor?.isActive({ textAlign: 'center' }) ? 'is-active' : ''}
                    title="가운데 정렬"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_align_center</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().setTextAlign('right').run()}
                    className={editor?.isActive({ textAlign: 'right' }) ? 'is-active' : ''}
                    title="오른쪽 정렬"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_align_right</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().setTextAlign('justify').run()}
                    className={editor?.isActive({ textAlign: 'justify' }) ? 'is-active' : ''}
                    title="양쪽 정렬"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_align_justify</span>
                </button>
            </div>

            <div className="separator" />

            {/* 7. Line Spacing */}
            <div className="group">
                <select
                    onChange={(e) => {
                        if (!editor) return;
                        (editor.chain().focus() as any).setLineHeight(e.target.value).run();
                    }}
                    value={editor?.getAttributes('paragraph').lineHeight || 'normal'}
                    disabled={!editor}
                    className="spacing-select"
                    title="선 및 문단 간격"
                >
                    <option value="normal">기본 간격</option>
                    <option value="1.0">1.0</option>
                    <option value="1.2">1.2</option>
                    <option value="1.5">1.5</option>
                    <option value="2.0">2.0</option>
                    <option value="2.5">2.5</option>
                    <option value="3.0">3.0</option>
                </select>
            </div>

            <div className="separator" />

            {/* 8. Lists */}
            <div className="group">
                <button
                    onClick={() => editor?.chain().focus().toggleBulletList().run()}
                    className={editor?.isActive('bulletList') ? 'is-active' : ''}
                    title="글머리표"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_list_bulleted</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().toggleOrderedList().run()}
                    className={editor?.isActive('orderedList') ? 'is-active' : ''}
                    title="문단번호"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">format_list_numbered</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().toggleTaskList().run()}
                    className={editor?.isActive('taskList') ? 'is-active' : ''}
                    title="체크박스"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">checklist</span>
                </button>
            </div>

            <div className="separator" />

            {/* 9. Advanced: Image, Table, Label */}
            <div className="group">
                <button
                    onClick={() => {
                        const url = window.prompt('이미지 URL을 입력하세요');
                        if (!url) return;
                        try {
                            const parsed = new URL(url);
                            if (!['http:', 'https:'].includes(parsed.protocol)) {
                                alert('http 또는 https URL만 허용됩니다.');
                                return;
                            }
                            editor?.chain().focus().setImage({ src: url }).run();
                        } catch {
                            alert('유효한 URL을 입력해주세요.');
                        }
                    }}
                    title="사진 삽입"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">add_photo_alternate</span>
                </button>
                <button
                    onClick={() => editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}
                    title="표 삽입"
                    disabled={!editor}
                >
                    <span className="material-symbols-outlined">grid_on</span>
                </button>
                <div className="color-picker-wrapper" title="라벨 추가 (하이라이트)">
                    <span className="material-symbols-outlined">label</span>
                    <input
                        type="color"
                        onChange={e => editor?.chain().focus().setHighlight({ color: e.target.value }).run()}
                        value={editor?.getAttributes('highlight').color || '#ffff00'}
                        disabled={!editor}
                    />
                </div>
            </div>

            <div className="separator" />

            {/* 10. Search & Settings */}
            <div className="search-group">
                <input
                    type="text"
                    placeholder="검색..."
                    value={searchValue}
                    onChange={(e) => setSearchValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    disabled={!editor}
                />
                <button onClick={handleSearch} disabled={!editor} title="검색">
                    <span className="material-symbols-outlined">search</span>
                </button>
            </div>

            <div className="separator" />

            <div className="group">
                <button
                    onClick={onOpenSettings}
                    className="settings-btn"
                    title="환경설정"
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--foreground)',
                        padding: '6px'
                    }}
                >
                    <Settings size={20} />
                </button>
            </div>
        </div>
    );
};
