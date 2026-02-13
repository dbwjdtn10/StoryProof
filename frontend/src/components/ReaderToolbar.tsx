import { useState, useRef, useEffect } from 'react';
import { Editor } from '@tiptap/react';
import {
    Bookmark,
    Highlighter,
    MessageSquare,
    Type,
    Palette,
    AlignJustify,
    Maximize,
    Plus,
    Minus,
    Check
} from 'lucide-react';

interface ReaderToolbarProps {
    editor: Editor | null;
    readerSettings: {
        fontSize: number;
        lineHeight: number;
        paragraphSpacing: number;
        contentWidth: number;
        fontFamily?: string;
        theme?: string;
    };
    onSettingsChange: (settings: any) => void;
    onBookmark: () => void;
    onHighlight: () => void;
    onAddMemo: () => void;
}

export const ReaderToolbar = ({
    editor,
    readerSettings,
    onSettingsChange,
    onBookmark,
    onHighlight,
    onAddMemo
}: ReaderToolbarProps) => {
    const [activePopover, setActivePopover] = useState<string | null>(null);
    const toolbarRef = useRef<HTMLDivElement>(null);

    // Close popover when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (toolbarRef.current && !toolbarRef.current.contains(event.target as Node)) {
                setActivePopover(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const togglePopover = (name: string) => {
        setActivePopover(activePopover === name ? null : name);
    };

    const handleReset = () => {
        onSettingsChange({
            fontSize: 18,
            lineHeight: 2.0,
            paragraphSpacing: 40,
            contentWidth: 80,
            fontFamily: 'Noto Sans KR',
            theme: 'light'
        });
        setActivePopover(null);
    };

    const fonts = [
        { name: 'Noto Sans KR', label: '기본 고딕 (Sans)' },
        { name: 'Noto Serif KR', label: '기본 명조 (Serif)' },
        { name: 'Nanum Myeongjo', label: '나눔 명조' },
        { name: 'Nanum Gothic', label: '나눔 고딕' },
        { name: 'Poppins', label: 'Poppins' },
        { name: 'Inter', label: 'Inter' }
    ];

    const themes = [
        { id: 'light', label: '라이트', color: '#ffffff', textColor: '#1a1a1a' },
        { id: 'sepia', label: '세피아', color: '#f4ecd8', textColor: '#5b4636' },
        { id: 'dark', label: '다크', color: '#1a1a1a', textColor: '#e5e7eb' }
    ];

    return (
        <div className="novel-toolbar reader-toolbar" ref={toolbarRef}>
            <div className="group">
                {/* 1. Typography (Size) */}
                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => togglePopover('typography')}
                        className={`toolbar-btn ${activePopover === 'typography' ? 'active' : ''}`}
                        title="글자 크기"
                    >
                        <Type size={20} />
                    </button>
                    {activePopover === 'typography' && (
                        <div className="reader-popover">
                            <div className="popover-header">글자 크기</div>
                            <div className="popover-row">
                                <button
                                    className="popover-btn-small"
                                    onClick={() => onSettingsChange({ ...readerSettings, fontSize: Math.max(12, readerSettings.fontSize - 1) })}
                                >
                                    <Minus size={16} />
                                </button>
                                <span style={{ minWidth: '30px', textAlign: 'center', fontWeight: 600 }}>{readerSettings.fontSize}</span>
                                <button
                                    className="popover-btn-small"
                                    onClick={() => onSettingsChange({ ...readerSettings, fontSize: Math.min(32, readerSettings.fontSize + 1) })}
                                >
                                    <Plus size={16} />
                                </button>
                                <button className="popover-btn-reset" onClick={handleReset}>초기화</button>
                            </div>
                        </div>
                    )}
                </div>

                {/* 2. Font Family */}
                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => togglePopover('font')}
                        className={`toolbar-btn ${activePopover === 'font' ? 'active' : ''}`}
                        title="글꼴 선택"
                    >
                        <span style={{ fontSize: '18px', fontWeight: 700 }}>A</span>
                    </button>
                    {activePopover === 'font' && (
                        <div className="reader-popover">
                            <div className="popover-header">글꼴</div>
                            {fonts.map(f => (
                                <div
                                    key={f.name}
                                    className={`popover-item ${readerSettings.fontFamily === f.name ? 'selected' : ''}`}
                                    onClick={() => {
                                        onSettingsChange({ ...readerSettings, fontFamily: f.name });
                                        setActivePopover(null);
                                    }}
                                >
                                    <span style={{ fontFamily: f.name }}>{f.label}</span>
                                    {readerSettings.fontFamily === f.name && <Check size={14} />}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 3. Theme */}
                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => togglePopover('theme')}
                        className={`toolbar-btn ${activePopover === 'theme' ? 'active' : ''}`}
                        title="테마 설정"
                    >
                        <Palette size={20} />
                    </button>
                    {activePopover === 'theme' && (
                        <div className="reader-popover">
                            <div className="popover-header">테마</div>
                            {themes.map(t => (
                                <div
                                    key={t.id}
                                    className={`popover-item ${readerSettings.theme === t.id ? 'selected' : ''}`}
                                    onClick={() => {
                                        onSettingsChange({ ...readerSettings, theme: t.id });
                                        setActivePopover(null);
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <div style={{
                                            width: '16px',
                                            height: '16px',
                                            borderRadius: '50%',
                                            backgroundColor: t.color,
                                            border: '1px solid #e2e8f0'
                                        }} />
                                        {t.label}
                                    </div>
                                    {readerSettings.theme === t.id && <Check size={14} />}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 4. Spacing (Line Height) */}
                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => togglePopover('spacing')}
                        className={`toolbar-btn ${activePopover === 'spacing' ? 'active' : ''}`}
                        title="줄 간격"
                    >
                        <AlignJustify size={20} />
                    </button>
                    {activePopover === 'spacing' && (
                        <div className="reader-popover">
                            <div className="popover-header">줄 간격</div>
                            {[
                                { val: 1.5, label: '표준' },
                                { val: 2.0, label: '넓음' },
                                { val: 2.5, label: '매우 넓음' }
                            ].map(s => (
                                <div
                                    key={s.val}
                                    className={`popover-item ${readerSettings.lineHeight === s.val ? 'selected' : ''}`}
                                    onClick={() => {
                                        onSettingsChange({ ...readerSettings, lineHeight: s.val });
                                        setActivePopover(null);
                                    }}
                                >
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <AlignJustify size={14} style={{ opacity: 0.5 }} />
                                        {s.label}
                                    </div>
                                    {readerSettings.lineHeight === s.val && <Check size={14} />}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 5. Width */}
                <div style={{ position: 'relative' }}>
                    <button
                        onClick={() => togglePopover('width')}
                        className={`toolbar-btn ${activePopover === 'width' ? 'active' : ''}`}
                        title="본문 너비"
                    >
                        <Maximize size={20} />
                    </button>
                    {activePopover === 'width' && (
                        <div className="reader-popover">
                            <div className="popover-header">본문 너비</div>
                            {[
                                { val: 70, label: '좁게' },
                                { val: 80, label: '표준' },
                                { val: 90, label: '넓게' },
                                { val: 100, label: '전체' }
                            ].map(w => (
                                <div
                                    key={w.val}
                                    className={`popover-item ${readerSettings.contentWidth === w.val ? 'selected' : ''}`}
                                    onClick={() => {
                                        onSettingsChange({ ...readerSettings, contentWidth: w.val });
                                        setActivePopover(null);
                                    }}
                                >
                                    <span>{w.label} ({w.val}%)</span>
                                    {readerSettings.contentWidth === w.val && <Check size={14} />}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="separator" style={{ margin: '0 8px' }} />

                {/* Action Buttons */}
                <button onClick={onBookmark} title="책갈피 추가" className="toolbar-btn">
                    <Bookmark size={20} />
                </button>
                <button onClick={onHighlight} disabled={!editor} title="하이라이트" className="toolbar-btn">
                    <Highlighter size={20} />
                </button>
                <button onClick={onAddMemo} disabled={!editor} title="메모 추가" className="toolbar-btn">
                    <MessageSquare size={20} />
                </button>
            </div>
        </div>
    );
};
