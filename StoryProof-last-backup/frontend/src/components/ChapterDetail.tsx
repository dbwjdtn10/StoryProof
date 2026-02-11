import { ArrowLeft, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Users, Package, Clock, Save, MapPin, Search, MessageCircle, Settings, Bookmark, List, ArrowRight } from 'lucide-react';
import { useState, useEffect } from 'react';
import { FloatingMenu } from './FloatingMenu';
import { ThemeToggle } from './ThemeToggle';
import { getChapter, updateChapter, getChapterBible, reanalyzeChapter, BibleData } from '../api/novel';
import { AnalysisResultModal, AnalysisResult } from './AnalysisResultModal';
import { NovelEditor } from './NovelEditor';
import { AuthorToolbar } from './AuthorToolbar';
import { ReaderToolbar } from './ReaderToolbar';
import { SettingsModal } from './SettingsModal';
import { Editor } from '@tiptap/react';
import '../novel-toolbar.css';

interface ChapterDetailProps {
    fileName: string;
    onBack: () => void;
    novelId?: number;
    chapterId?: number;
    mode?: 'reader' | 'writer';
}

export function ChapterDetail({ fileName, onBack, novelId, chapterId, mode }: ChapterDetailProps) {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isCharactersOpen, setIsCharactersOpen] = useState(true);
    const [isItemsOpen, setIsItemsOpen] = useState(false);
    const [isLocationsOpen, setIsLocationsOpen] = useState(false);
    const [isKeyEventsOpen, setIsKeyEventsOpen] = useState(false);
    const [isTocOpen, setIsTocOpen] = useState(true);

    const [content, setContent] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [initialLoadDone, setInitialLoadDone] = useState(false);

    const [bibleData, setBibleData] = useState<BibleData | null>(null);
    const [isBibleLoading, setIsBibleLoading] = useState(false);
    const [sceneTexts, setSceneTexts] = useState<string[]>([]);

    const [chapterStatus, setChapterStatus] = useState<'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | undefined>(undefined);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    // Tiptap Editor state
    const [activeEditor, setActiveEditor] = useState<Editor | null>(null);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    // Reader Mode Enhancements State
    const [readerSettings, setReaderSettings] = useState(() => {
        const saved = localStorage.getItem(`readerSettings_${novelId || 'default'}`);
        return saved ? JSON.parse(saved) : {
            fontSize: 18,
            lineHeight: 2.0,
            paragraphSpacing: 40,
            contentWidth: 80,
            fontFamily: 'Noto Sans KR',
            theme: 'light'
        };
    });

    const [scrollProgress, setScrollProgress] = useState(0);
    const [bookmark, setBookmark] = useState<number | null>(null);

    // Persist reader settings
    useEffect(() => {
        if (novelId) {
            localStorage.setItem(`readerSettings_${novelId}`, JSON.stringify(readerSettings));
            // Apply to document variables
            const root = document.querySelector('.chapter-detail-container') as HTMLElement;
            if (root) {
                root.style.setProperty('--reader-font-size', `${readerSettings.fontSize}px`);
                root.style.setProperty('--reader-line-height', `${readerSettings.lineHeight}`);
                root.style.setProperty('--reader-paragraph-spacing', `${readerSettings.paragraphSpacing}px`);
                root.style.setProperty('--reader-content-width', `${readerSettings.contentWidth}%`);
                root.style.setProperty('--reader-font-family', readerSettings.fontFamily || 'Noto Sans KR');

                // Theme application
                if (readerSettings.theme === 'dark') {
                    root.style.setProperty('--reader-bg', '#1a1a1a');
                    root.style.setProperty('--reader-text', '#e5e7eb');
                } else if (readerSettings.theme === 'sepia') {
                    root.style.setProperty('--reader-bg', '#f4ecd8');
                    root.style.setProperty('--reader-text', '#5b4636');
                } else {
                    root.style.setProperty('--reader-bg', '#ffffff');
                    root.style.setProperty('--reader-text', '#1a1a1a');
                }
            }
        }
    }, [readerSettings, novelId]);

    // Highlight State
    const [highlightData, setHighlightData] = useState<{
        sceneIndex: number;
        text: string;
        timestamp: number;
    } | null>(null);

    const [scrollState, setScrollState] = useState({ scrollTop: 0, scrollHeight: 1 });

    // Handle scroll for progress bar and bookmarking
    const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
        const target = e.currentTarget;
        const progress = (target.scrollTop / (target.scrollHeight - target.clientHeight)) * 100;
        setScrollProgress(progress);
        setScrollState({ scrollTop: target.scrollTop, scrollHeight: target.scrollHeight });

        // Auto-bookmark: Save current scroll position every few seconds (throttled)
        if (mode === 'reader' && chapterId) {
            localStorage.setItem(`bookmark_${chapterId}`, target.scrollTop.toString());
        }
    };

    // Load bookmark on initial load
    useEffect(() => {
        if (mode === 'reader' && chapterId && initialLoadDone) {
            const savedScroll = localStorage.getItem(`bookmark_${chapterId}`);
            if (savedScroll) {
                const container = document.querySelector('.scenes-container');
                if (container) {
                    setTimeout(() => {
                        container.scrollTop = parseInt(savedScroll);
                    }, 500);
                }
            }
        }
    }, [mode, chapterId, initialLoadDone]);

    // AI Dictionary Selection State
    const [selectedText, setSelectedText] = useState("");
    const [selectionCoords, setSelectionCoords] = useState<{ x: number, y: number } | null>(null);

    const handleTextSelection = () => {
        const selection = window.getSelection();
        const text = selection?.toString().trim();

        if (text && text.length > 0) {
            const range = selection?.getRangeAt(0);
            const rect = range?.getBoundingClientRect();
            if (rect) {
                setSelectedText(text);
                setSelectionCoords({
                    x: rect.left + (rect.width / 2),
                    y: rect.top - 40 // Use client rect directly for fixed popup
                });
            }
        } else {
            setSelectionCoords(null);
        }
    };

    const handleHighlight = () => {
        if (!activeEditor) {
            alert("텍스트를 먼저 선택해주세요 (편집기가 활성화되어야 합니다).");
            return;
        }
        activeEditor.chain().focus().setHighlight({ color: '#ffcc00' }).run();
        setSelectionCoords(null);
        alert("하이라이트가 적용되었습니다.");
    };

    const handleAddMemo = () => {
        if (!activeEditor) {
            alert("텍스트를 먼저 선택해주세요.");
            return;
        }
        const memo = prompt("메모를 입력하세요:");
        if (memo) {
            activeEditor.chain().focus().setHighlight({ color: '#ccffcc' }).run();
            // TODO: Save to annotations state/localStorage
            alert(`메모가 저장되었습니다: ${memo}`);
        }
        setSelectionCoords(null);
    };

    const handleManualBookmark = () => {
        const container = document.querySelector('.scenes-container');
        if (container) {
            const pos = container.scrollTop;
            if (chapterId) {
                localStorage.setItem(`bookmark_${chapterId}`, pos.toString());
                alert("현재 독서 위치가 책갈피로 저장되었습니다.");
            }
        }
    };

    const handleOpenAIdictionary = () => {
        alert(`'${selectedText}'에 대한 AI 어휘 사전 설명을 생성합니다...`);
        setSelectionCoords(null);
    };

    // Track which scene is currently being edited
    const [editingSceneIndex, setEditingSceneIndex] = useState<number | null>(null);

    // Clear highlight after 15 seconds
    useEffect(() => {
        if (highlightData) {
            const timer = setTimeout(() => {
                setHighlightData(null);
            }, 15000);
            return () => clearTimeout(timer);
        }
    }, [highlightData]);

    // Helper to render text with highlights in Read Mode
    const renderSceneContent = (text: string, index: number) => {
        const highlightTerm = (highlightData && highlightData.sceneIndex === index) ? highlightData.text : null;

        if (!highlightTerm) {
            return <div className="scene-text-content">{text}</div>;
        }

        const escapedTerm = highlightTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const parts = text.split(new RegExp(`(${escapedTerm})`, 'g'));

        return (
            <div className="scene-text-content">
                {parts.map((part, i) =>
                    part === highlightTerm ? (
                        <span key={i} className="highlight-mark">{part}</span>
                    ) : (
                        <span key={i}>{part}</span>
                    )
                )}
            </div>
        );
    };

    useEffect(() => {
        if (novelId && chapterId) {
            loadChapterContent();
            loadBibleData();
        } else {
            // Fallback for demo or if IDs missing (though they should be passed now)
            // Keep sample text if no real data
            if (!initialLoadDone) {
                setContent(`앨리스는 언니 옆에 앉아 할일 없이 강둑에 앉아있는 게 지루해지기 시작했어요.
그러다 한두 번 언니가 읽고 있는 책에 눈길을 주기도 했지만 그림이나 대화 하나 없는 책이지 뭐예요.
"그림이나 대화도 없는 책이 무슨 소용이람?" 앨리스는 생각했어요.

그래서 앨리스는 (더운 날씨 때문에 머리가 멍해져서 졸리긴 했지만) 데이지 화환을 만드는 즐거움이 일어나서 데이지를 따러 가는 수고를 감수할 만한 가치가 있을지 곰곰이 생각하고 있었어요. 바로 그때 분홍색 눈을 한 흰 토끼 한 마리가 앨리스 가까이를 지나갔어요.

이건 그다지 놀라운 일이 아니었어요. 앨리스는 토끼가 혼잣말로 "이런, 이런! 늦겠어!"라고 말하는 걸 들었을 때도 그게 그렇게 이상하다고 생각하지 않았어요. (나중에 생각해 보니 이상하게 여겼어야 했지만, 그때는 모든 게 너무나 자연스러워 보였거든요.) 하지만 토끼가 실제로 조끼 주머니에서 시계를 꺼내 보더니 서둘러 달려가는 걸 보자, 앨리스는 벌떡 일어났어요. 조끼 주머니가 달린 토끼도, 거기서 꺼낼 시계를 가진 토끼도 본 적이 없다는 생각이 번뜩 스쳤거든요. 호기심에 불타 앨리스는 들판을 가로질러 토끼를 쫓아갔고, 토끼가 울타리 밑 큰 토끼 굴로 뛰어들어 가는 걸 보았어요.`);
                setInitialLoadDone(true);
            }
        }
    }, [novelId, chapterId]);

    // Polling for status updates
    useEffect(() => {
        let intervalId: NodeJS.Timeout;

        if (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING') {
            intervalId = setInterval(async () => {
                if (!novelId || !chapterId) return;
                try {
                    const chapterData = await getChapter(novelId, chapterId);
                    console.log(`[Polling] Current Status: ${chapterData.storyboard_status}`);

                    const terminalStatuses = ['COMPLETED', 'FAILED'];
                    const rawStatus = chapterData.storyboard_status || '';
                    const currentStatus = rawStatus.toUpperCase();

                    if (terminalStatuses.includes(currentStatus)) {
                        console.log(`[Polling] Terminal state reached: ${currentStatus}`);
                        setChapterStatus(currentStatus as any);
                        setIsAnalyzing(false);
                        // Refresh Bible data when analysis is done
                        if (chapterData.storyboard_status === 'COMPLETED') {
                            alert("분석이 완료되었습니다! 데이터를 새로고침합니다.");
                            loadChapterContent();
                            loadBibleData();
                        } else if (chapterData.storyboard_status === 'FAILED') {
                            alert(`분석 실패: ${chapterData.storyboard_message || '알 수 없는 오류'}`);
                        }
                    }
                } catch (error) {
                    console.error("Status check failed", error);
                }
            }, 3000); // Check every 3 seconds
        }

        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [chapterStatus, novelId, chapterId]);

    const loadChapterContent = async () => {
        if (!novelId || !chapterId) {
            return;
        }
        setIsLoading(true);
        try {
            const chapter = await getChapter(novelId, chapterId);
            setContent(chapter.content);
            setChapterStatus(chapter.storyboard_status);
        } catch (error) {
            alert("소설 내용을 불러오는데 실패했습니다.");
        } finally {
            setIsLoading(false);
            setInitialLoadDone(true);
        }
    };

    const loadBibleData = async () => {
        if (!novelId || !chapterId) {
            return;
        }
        setIsBibleLoading(true);
        try {
            const bible = await getChapterBible(novelId, chapterId);
            setBibleData(bible);
            if (bible.scenes && bible.scenes.length > 0) {
                // 과도한 줄바꿈 제거: 연속된 2개 이상의 줄바꿈을 1개로 축소
                setSceneTexts(bible.scenes.map(s =>
                    s.original_text.trim().replace(/\n{2,}/g, '\n')
                ));
            }
        } catch (error) {
            // 바이블 데이터가 없어도 계속 진행
        } finally {
            setIsBibleLoading(false);
        }
    };

    const handleSave = async () => {
        if (!novelId || !chapterId) return;
        setIsSaving(true);
        try {
            const finalContent = sceneTexts.length > 0
                ? sceneTexts.map(s => s.trim()).join("\n\n")
                : content;

            // 씬 데이터가 있으면 함께 저장 요청 (벡터 DB 업데이트용)
            await updateChapter(novelId, chapterId, {
                content: finalContent,
                scenes: sceneTexts.length > 0 ? sceneTexts : undefined
            });
            alert("서버에 저장되었습니다.");

            // 로컬 파일 저장 트리거
            handleLocalSave();
        } catch (error) {
            alert("저장에 실패했습니다.");
        } finally {
            setIsSaving(false);
        }
    };

    const handleLocalSave = () => {
        const finalContent = sceneTexts.length > 0
            ? sceneTexts.map(s => s.trim()).join("\n\n")
            : content;

        const blob = new Blob([finalContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${fileName || 'chapter'}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const [selectedCharacter, setSelectedCharacter] = useState<any | null>(null);
    const [selectedItem, setSelectedItem] = useState<any | null>(null);
    const [selectedKeyEvent, setSelectedKeyEvent] = useState<any | null>(null);
    const [selectedExtraItem, setSelectedExtraItem] = useState<{ title: string, item: any } | null>(null);

    // 설정 파괴 분석 상태
    const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
    const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

    const [selectedLocation, setSelectedLocation] = useState<any | null>(null);
    const [extraSectionStates, setExtraSectionStates] = useState<Record<string, boolean>>({});
    const [isAppearancesExpanded, setIsAppearancesExpanded] = useState(false);
    const [isItemAppearancesExpanded, setIsItemAppearancesExpanded] = useState(false);
    const [isLocationAppearancesExpanded, setIsLocationAppearancesExpanded] = useState(false);

    const scrollToScene = (index: number, highlightText?: string) => {
        // Close all modals first
        setSelectedCharacter(null);
        setSelectedItem(null);
        setSelectedKeyEvent(null);
        setSelectedExtraItem(null);
        setSelectedLocation(null);
        setIsAppearancesExpanded(false);
        setIsItemAppearancesExpanded(false);
        setIsLocationAppearancesExpanded(false);

        // Set highlight if provided and not empty
        if (highlightText && highlightText.trim()) {
            setHighlightData({
                sceneIndex: index,
                text: highlightText.trim(),
                timestamp: Date.now()
            });
        }

        // Wait for state updates and then scroll
        setTimeout(() => {
            const element = document.getElementById(`scene-block-${index}`);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Optional: Highlight effect for the block itself
                element.style.transition = 'background-color 0.5s';
                element.style.backgroundColor = 'rgba(79, 70, 229, 0.1)';
                setTimeout(() => {
                    element.style.backgroundColor = 'transparent';
                }, 1000);
            }
        }, 100);
    };

    // 설정 파괴 분석 실행
    const handleCheckConsistency = async () => {
        setIsAnalysisModalOpen(true);
        setIsAnalysisLoading(true);
        setAnalysisResult(null);

        try {
            // 현재 모든 씬의 텍스트를 합쳐서 분석 요청 (씬 모드 vs 에디터 모드)
            const allText = sceneTexts.length > 0
                ? sceneTexts.join('\n\n')
                : content;

            // Get selected model from settings
            const selectedModel = localStorage.getItem('llm_model') || 'gemini-2.5-flash';

            const response = await fetch(`http://localhost:8000/api/v1/analysis/consistency`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_id: novelId,
                    chapter_id: chapterId,
                    text: allText,
                    model: selectedModel
                })
            });

            if (!response.ok) throw new Error('분석 요청 실패');

            const { task_id } = await response.json();

            // 폴링 시작
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch(`http://localhost:8000/api/v1/analysis/task/${task_id}`);
                    const data = await statusRes.json();

                    if (data.status === "COMPLETED") {
                        clearInterval(pollInterval);
                        setAnalysisResult(data.result);
                        setIsAnalysisLoading(false);
                    } else if (data.status === "FAILED") {
                        clearInterval(pollInterval);
                        setAnalysisResult({ status: "분석 실패", message: data.error });
                        setIsAnalysisLoading(false);
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                }
            }, 2000);

            // 컴포넌트 언마운트 시 인터벌 클리어를 위해 (실제로는 cleanup에서 처리해야 하지만 여기서는 로직 단순화)
        } catch (error) {
            console.error("Analysis error:", error);
            setAnalysisResult({ status: "오류 발생", message: "서버와 통신 중 오류가 발생했습니다." });
            setIsAnalysisLoading(false);
        }
    };

    const handleNavigateToQuote = (quote: string) => {
        if (!quote) return;

        // 정규화 함수: 공백과 줄바꿈을 단순화하여 비교
        const normalize = (str: string) => str.replace(/\s+/g, ' ').trim();
        const targetQ = normalize(quote);

        // 1. Scene Mode Navigation (sceneTexts exists)
        if (sceneTexts.length > 0) {
            // Find the scene containing the quote
            const sceneIndex = sceneTexts.findIndex((s: string) => normalize(s).includes(targetQ));

            if (sceneIndex !== -1) {
                // Determine the exact substring to highlight within the original text
                // This is a best-effort match since we normalized both
                const originalText = sceneTexts[sceneIndex];
                // Simple heuristic: try to find the quote roughly
                // If exact match fails, we still scroll to the scene but might not highlight perfectly
                scrollToScene(sceneIndex, quote);
            } else {
                alert('해당 문장을 본문에서 찾을 수 없습니다.');
            }
        }
        // 2. Single Textarea Mode (content)
        else {
            const textArea = document.querySelector('.novel-text-editor') as HTMLTextAreaElement;
            if (textArea && content) {
                // Find position
                // Simple exact match first
                let pos = content.indexOf(quote);

                // If not found, try normalized match logic (harder in textarea selection)
                if (pos === -1) {
                    // Try to find by splitting and matching parts? 
                    // For now, let's just alert if exact match fails in raw mode, 
                    // or improved searching could be added later.
                    const normalizedContent = normalize(content);
                    if (normalizedContent.includes(targetQ)) {
                        alert("문장을 찾았으나, 텍스트 에디터 모드에서는 정확한 위치로 이동하기 어렵습니다. (줄바꿈 차이 등)");
                        return;
                    }
                }

                if (pos !== -1) {
                    textArea.focus();
                    textArea.setSelectionRange(pos, pos + quote.length);
                    // Scroll to cursor
                    const fullText = textArea.value;
                    const textBefore = fullText.substring(0, pos);
                    const lines = textBefore.split("\n").length;
                    const lineHeight = 24; // approximate
                    textArea.scrollTop = (lines - 1) * lineHeight;
                } else {
                    alert('해당 문장을 본문에서 찾을 수 없습니다.');
                }
            }
        }
    };

    const adjustTextareaHeight = (element: HTMLTextAreaElement) => {
        element.style.height = 'auto';
        element.style.height = `${element.scrollHeight}px`;
    };

    // ... (rest of the setup)

    // 바이블 데이터 또는 기본 샘플 데이터
    const characters = bibleData?.characters && bibleData.characters.length > 0
        ? bibleData.characters
        : [
            { name: '앨리스', first_appearance: 0, appearance_count: 5, appearances: [0, 1, 2, 3, 4], traits: ['호기심 많음', '상상력 풍부'] },
            { name: '흰 토끼', first_appearance: 0, appearance_count: 3, appearances: [0, 1, 3], traits: ['바쁨', '걱정 많음'] },
            { name: '언니', first_appearance: 0, appearance_count: 1, appearances: [0] },
        ];

    const items = bibleData?.items && bibleData.items.length > 0
        ? bibleData.items
        : [
            { name: '시계', first_appearance: 0 },
            { name: '책', first_appearance: 0 },
            { name: '데이지 화환', first_appearance: 0 },
        ];

    const key_events = bibleData?.key_events && bibleData.key_events.length > 0
        ? bibleData.key_events
        : [
            { summary: '앨리스가 언니 옆 강둑에 앉아 있음', scene_index: 0, importance: '하' },
            { summary: '흰 토끼가 지나가는 것을 목격', scene_index: 1, importance: '중' },
            { summary: '토끼를 따라 토끼 굴로 들어감', scene_index: 2, importance: '상' },
        ];

    const handleReanalyze = async () => {
        if (!novelId || !chapterId) return;

        if (chapterStatus === 'PROCESSING') {
            alert("현재 분석이 진행 중입니다. 잠시만 기다려주세요.");
            return;
        }

        if (!confirm("재분석을 진행하시겠습니까?\n기존 분석 데이터(인물, 사건 등)가 덮어씌워질 수 있습니다.")) {
            return;
        }

        setIsAnalyzing(true);
        setChapterStatus('PROCESSING');
        try {
            await reanalyzeChapter(novelId, chapterId);
            alert("재분석 요청이 완료되었습니다. 백그라운드에서 분석이 진행됩니다.\n(완료 시까지 버튼이 비활성화됩니다)");
        } catch (error) {
            console.error(error);
            alert("재분석 요청 실패");
            setChapterStatus('FAILED');
            setIsAnalyzing(false);
        }
    };

    const locations = bibleData?.locations && bibleData.locations.length > 0
        ? bibleData.locations
        : [
            { name: '강둑', description: '언니와 함께 앉아있던 곳', scenes: [0] },
            { name: '토끼 굴', description: '토끼가 들어간 긴 굴', scenes: [2] },
        ];

    // ... (rest of items/timeline)

    if (isLoading && !initialLoadDone) {
        return (
            <div className={`chapter-detail-container loading ${isSidebarOpen ? 'sidebar-open' : ''}`}>
                <div className="loading-spinner"></div>
            </div>
        );
    }

    // ... (rest)
    return (
        <div className={`chapter-detail-container ${isSidebarOpen ? 'sidebar-open' : ''}`}>
            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                .spin-animation { animation: spin 1s linear infinite; }
            `}</style>
            {/* Header */}
            {/* Header */}
            <div className="chapter-detail-header" style={{
                display: 'flex',
                alignItems: 'center',
                padding: '16px 24px',
                borderBottom: '1px solid #E5E7EB',
                backgroundColor: 'white',
            }}>
                <button className="back-button" onClick={onBack} style={{
                    marginRight: '16px',
                    padding: '8px',
                    borderRadius: '50%',
                    border: 'none',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <ArrowLeft size={24} color="#4B5563" />
                </button>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <h1 className="chapter-detail-title" style={{
                        fontSize: '1.25rem',
                        fontWeight: 600,
                        color: '#1F2937',
                        margin: 0
                    }}>{fileName}</h1>
                    <span style={{
                        padding: '4px 10px',
                        borderRadius: '12px',
                        backgroundColor: mode === 'reader' ? '#E0F2FE' : '#EEF2FF',
                        color: mode === 'reader' ? '#0369A1' : '#4F46E5',
                        fontSize: '12px',
                        fontWeight: 600,
                        border: mode === 'reader' ? '1px solid #BAE6FD' : '1px solid #C7D2FE'
                    }}>
                        {mode === 'reader' ? '📖 독자 모드' : '✍️ 작가 모드'}
                    </span>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                        className="reanalyze-button"
                        onClick={handleReanalyze}
                        disabled={chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                            backgroundColor: 'white', color: '#4F46E5', border: '1px solid #4F46E5', borderRadius: '6px',
                            cursor: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? 'not-allowed' : 'pointer',
                            fontSize: '0.9rem', fontWeight: 500
                        }}
                    >
                        <Clock size={16} />
                        {mode === 'reader' ? '심층 해설' : '설정 분석'}
                    </button>
                    {mode !== 'reader' && (
                        <button
                            className="save-button"
                            onClick={handleSave}
                            disabled={isSaving}
                            style={{
                                display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 16px',
                                backgroundColor: '#4F46E5', color: 'white', border: 'none', borderRadius: '6px',
                                cursor: isSaving ? 'wait' : 'pointer', fontSize: '0.9rem', fontWeight: 500
                            }}
                        >
                            <Save size={18} />
                            저장
                        </button>
                    )}
                </div>
            </div>

            {/* Sticky Toolbars */}
            <div style={{ position: 'sticky', top: 0, zIndex: 40, backgroundColor: 'white' }}>
                {mode === 'reader' && (
                    <div className="reading-progress-bar" style={{ width: `${scrollProgress}%`, top: '72px' }} />
                )}
                {mode === 'reader' ? (
                    <ReaderToolbar
                        editor={activeEditor}
                        readerSettings={readerSettings}
                        onSettingsChange={setReaderSettings}
                        onBookmark={handleManualBookmark}
                        onHighlight={handleHighlight}
                        onAddMemo={handleAddMemo}
                        onOpenSettings={() => setIsSettingsOpen(true)}
                    />
                ) : (
                    <AuthorToolbar
                        editor={activeEditor}
                        onOpenSettings={() => setIsSettingsOpen(true)}
                    />
                )}
            </div>


            {/* Main Layout */}
            <div className="chapter-detail-layout">
                {/* Sidebar */}
                <div className={`dictionary-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
                    {/* Table of Contents Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isTocOpen ? 'active' : ''}`}
                            onClick={() => setIsTocOpen(!isTocOpen)}
                        >
                            <div className="section-header-content">
                                <List size={18} />
                                <h3 className="section-title">목차 (장면 이동)</h3>
                            </div>
                            {isTocOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isTocOpen && (
                            <div className="section-content">
                                {sceneTexts.length > 0 ? (
                                    sceneTexts.map((_, index) => (
                                        <div
                                            key={index}
                                            className="section-item interactable"
                                            onClick={() => scrollToScene(index)}
                                            style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
                                        >
                                            <div className="item-name" style={{ margin: 0 }}>장면 {index + 1}</div>
                                            <ArrowRight size={14} color="#9CA3AF" />
                                        </div>
                                    ))
                                ) : (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>결과가 없습니다.</div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Characters Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isCharactersOpen ? 'active' : ''}`}
                            onClick={() => setIsCharactersOpen(!isCharactersOpen)}
                        >
                            <div className="section-header-content">
                                <Users size={18} />
                                <h3 className="section-title">인물</h3>
                            </div>
                            {isCharactersOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isCharactersOpen && (
                            <div className="section-content">
                                {isBibleLoading ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>로딩 중...</div>
                                ) : (
                                    characters.map((character, index) => (
                                        <div
                                            key={index}
                                            className="section-item interactable"
                                            onClick={() => setSelectedCharacter(character)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <div className="item-name">{character.name}</div>
                                            <div className="item-description">
                                                {character.traits && character.traits.length > 0
                                                    ? (
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                                                            {character.traits.slice(0, 3).map((trait, i) => (
                                                                <span key={i} style={{
                                                                    fontSize: '10px',
                                                                    padding: '2px 6px',
                                                                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                                                                    color: '#4F46E5',
                                                                    borderRadius: '4px'
                                                                }}>
                                                                    {trait}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    )
                                                    : (typeof (character as any).description === 'string' && (character as any).description
                                                        ? (character as any).description.slice(0, 30) + "..."
                                                        : `등장: ${character.appearance_count}회`)
                                                }
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>

                    {/* Items Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isItemsOpen ? 'active' : ''}`}
                            onClick={() => setIsItemsOpen(!isItemsOpen)}
                        >
                            <div className="section-header-content">
                                <Package size={18} />
                                <h3 className="section-title">아이템</h3>
                            </div>
                            {isItemsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isItemsOpen && (
                            <div className="section-content">
                                {items.map((item, index) => (
                                    <div
                                        key={index}
                                        className="section-item interactable"
                                        onClick={() => setSelectedItem(item)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <div className="item-name">{item.name}</div>
                                        <div className="item-description">
                                            {typeof (item as any).description === 'string' && (item as any).description
                                                ? (item as any).description
                                                : `첫 등장: ${(item as any).first_appearance + 1}씬`}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Locations Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isLocationsOpen ? 'active' : ''}`}
                            onClick={() => setIsLocationsOpen(!isLocationsOpen)}
                        >
                            <div className="section-header-content">
                                <MapPin size={18} />
                                <h3 className="section-title">장소</h3>
                            </div>
                            {isLocationsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isLocationsOpen && (
                            <div className="section-content">
                                {locations.map((location, index) => (
                                    <div
                                        key={index}
                                        className="section-item interactable"
                                        onClick={() => setSelectedLocation(location)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <div className="item-name">{location.name}</div>
                                        <div className="item-description">
                                            {typeof (location as any).description === 'string' && (location as any).description
                                                ? (location as any).description
                                                : `등장: ${(location as any).scenes?.length || 0}회`}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    {/* Key Events Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isKeyEventsOpen ? 'active' : ''}`}
                            onClick={() => setIsKeyEventsOpen(!isKeyEventsOpen)}
                        >
                            <div className="section-header-content">
                                <Clock size={18} />
                                <h3 className="section-title">주요 사건</h3>
                            </div>
                            {isKeyEventsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isKeyEventsOpen && (
                            <div className="section-content">
                                {key_events.map((event, index) => (
                                    <div
                                        key={index}
                                        className="section-item interactable"
                                        onClick={() => setSelectedKeyEvent(event)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <div className="item-name" style={{ fontSize: '0.95rem' }}>
                                            {event.summary && event.summary.length > 20
                                                ? event.summary.substring(0, 20) + "..."
                                                : event.summary}
                                        </div>
                                        <div className="item-description">
                                            {event.scene_index !== undefined ? `${event.scene_index + 1}씬` : ''}
                                            {event.importance && ` • 중요도: ${event.importance}`}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Dynamic Sections for Extra Keys */}
                    {bibleData && Object.keys(bibleData).filter(key => !['characters', 'items', 'timeline', 'locations', 'key_events', 'scenes'].includes(key)).map(key => {
                        const data = bibleData[key];
                        if (!Array.isArray(data)) return null;

                        const isOpen = extraSectionStates[key] ?? false;

                        return (
                            <div className="sidebar-section" key={key}>
                                <button
                                    className={`section-header ${isOpen ? 'active' : ''}`}
                                    onClick={() => setExtraSectionStates(prev => ({ ...prev, [key]: !prev[key] }))}
                                >
                                    <div className="section-header-content">
                                        <Package size={18} /> {/* Generic Icon */}
                                        <h3 className="section-title">{key.toUpperCase()}</h3>
                                    </div>
                                    {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                                </button>
                                {isOpen && (
                                    <div className="section-content">
                                        {data.map((item, index) => (
                                            <div
                                                key={index}
                                                className="section-item interactable"
                                                onClick={() => setSelectedExtraItem({ title: key, item })}
                                                style={{ cursor: 'pointer' }}
                                            >
                                                <div className="item-name">{item.name || item.title || `Item ${index + 1}`}</div>
                                                <div className="item-description">
                                                    {item.description || item.summary || (typeof item === 'string' ? item : JSON.stringify(item).slice(0, 50))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Toggle Button */}
                <button
                    className="dictionary-toggle"
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                >
                    {isSidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
                </button>

                <div
                    className="text-area"
                    style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
                    onMouseUp={handleTextSelection}
                >
                    <div className="text-content" style={{ flex: 1, padding: 0, height: '100%' }}>
                        {isLoading ? (
                            <div style={{ padding: '20px', textAlign: 'center' }}>로딩 중...</div>
                        ) : sceneTexts.length > 0 ? (
                            <div
                                className="scenes-container"
                                onScroll={handleScroll}
                                style={{
                                    height: '100%',
                                    overflowY: 'auto',
                                    padding: '20px',
                                    backgroundColor: 'var(--reader-bg, #ffffff)',
                                    color: 'var(--reader-text, #1a1a1a)',
                                    transition: 'background-color 0.3s ease, color 0.3s ease'
                                }}
                            >
                                {sceneTexts.map((text, index) => (
                                    <div
                                        key={index}
                                        id={`scene-block-${index}`}
                                        className="scene-block"
                                        style={{ position: 'relative', marginBottom: '60px' }}
                                    >
                                        <div style={{
                                            position: 'absolute',
                                            top: '-12px',
                                            left: '10px',
                                            fontSize: '12px',
                                            fontWeight: 'bold',
                                            color: '#6366f1',
                                            backgroundColor: '#f5f5f5',
                                            padding: '2px 8px',
                                            borderRadius: '12px',
                                            border: '1px solid #e0e7ff',
                                            zIndex: 5
                                        }}>
                                            Scene {index + 1}
                                        </div>

                                        <div className="scene-content-wrapper">
                                            <NovelEditor
                                                content={text}
                                                onUpdate={(html) => {
                                                    const newScenes = [...sceneTexts];
                                                    newScenes[index] = html;
                                                    setSceneTexts(newScenes);
                                                }}
                                                onFocus={(editor) => setActiveEditor(editor)}
                                                onCreated={(editor) => {
                                                    if (index === 0 && !activeEditor) {
                                                        setActiveEditor(editor);
                                                    }
                                                }}
                                                editable={mode !== 'reader'}

                                                placeholder={`장면 ${index + 1}의 내용을 입력하세요...`}
                                                className="tiptap-editor-scene"
                                            />
                                        </div>
                                    </div>
                                ))}

                                {mode === 'reader' && (
                                    <div className="reader-nav-buttons">
                                        <button
                                            className="nav-btn"
                                            onClick={() => alert("이전 화 이동 기능은 준비 중입니다.")}
                                        >
                                            <span className="nav-btn-label">이전 화</span>
                                            <span className="nav-btn-title">이전 장이 없습니다</span>
                                        </button>
                                        <button
                                            className="nav-btn"
                                            onClick={() => alert("다음 화 이동 기능은 준비 중입니다.")}
                                        >
                                            <span className="nav-btn-label">다음 화</span>
                                            <span className="nav-btn-title">다음 장으로 가기</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <NovelEditor
                                content={content}
                                onUpdate={(html) => setContent(html)}
                                onFocus={(editor) => setActiveEditor(editor)}
                                onCreated={(editor) => {
                                    if (!activeEditor) {
                                        setActiveEditor(editor);
                                    }
                                }}
                                editable={mode !== 'reader'}
                                placeholder="소설 내용을 입력하세요..."
                                className="tiptap-editor-full"
                            />
                        )}
                        {selectionCoords && (
                            <div
                                style={{
                                    position: 'fixed',
                                    top: selectionCoords.y,
                                    left: selectionCoords.x,
                                    transform: 'translateX(-50%)',
                                    backgroundColor: 'white',
                                    borderRadius: '24px',
                                    padding: '4px 8px',
                                    boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
                                    zIndex: 1000,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    border: '1px solid #E5E7EB'
                                }}
                            >
                                <button
                                    onClick={handleHighlight}
                                    style={{
                                        padding: '8px 12px',
                                        background: 'none',
                                        border: 'none',
                                        borderRadius: '20px',
                                        fontSize: '13px',
                                        fontWeight: 600,
                                        color: '#374151',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px'
                                    }}
                                    title="하이라이트"
                                >
                                    <div style={{ width: '14px', height: '14px', backgroundColor: '#ffcc00', borderRadius: '2px' }} />
                                    강조
                                </button>
                                <div style={{ width: '1px', height: '16px', backgroundColor: '#E5E7EB' }} />
                                <button
                                    onClick={handleAddMemo}
                                    style={{
                                        padding: '8px 12px',
                                        background: 'none',
                                        border: 'none',
                                        borderRadius: '20px',
                                        fontSize: '13px',
                                        fontWeight: 600,
                                        color: '#374151',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px'
                                    }}
                                    title="메모 추가"
                                >
                                    <MessageCircle size={16} />
                                    메모
                                </button>
                                <div style={{ width: '1px', height: '16px', backgroundColor: '#E5E7EB' }} />
                                <button
                                    onClick={handleOpenAIdictionary}
                                    style={{
                                        padding: '8px 12px',
                                        background: 'none',
                                        border: 'none',
                                        borderRadius: '20px',
                                        fontSize: '13px',
                                        fontWeight: 600,
                                        color: '#0369A1',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px'
                                    }}
                                >
                                    <Search size={16} />
                                    AI 사전
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Character Detail Modal */}
            {
                selectedCharacter && (
                    <div
                        className="modal-overlay"
                        onClick={() => setSelectedCharacter(null)}
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: 'rgba(0,0,0,0.5)',
                            zIndex: 1000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <div
                            className="modal-content"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                backgroundColor: 'var(--bg-card, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--text-primary, #333)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{selectedCharacter.name}</h2>
                                <button
                                    onClick={() => setSelectedCharacter(null)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                                >
                                    <Users size={20} />
                                </button>
                            </div>

                            {selectedCharacter.aliases && selectedCharacter.aliases.length > 0 && (
                                <div style={{ marginBottom: '16px' }}>
                                    <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '4px' }}>별칭</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        {selectedCharacter.aliases.map((alias: string, i: number) => (
                                            <span key={i} style={{
                                                fontSize: '0.8rem',
                                                padding: '2px 8px',
                                                backgroundColor: '#f1f5f9',
                                                borderRadius: '12px',
                                                color: '#475569'
                                            }}>
                                                {alias}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '4px' }}>설명</div>
                                <p style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0 }}>
                                    {selectedCharacter.description || "상세 설명이 없습니다."}
                                </p>
                            </div>

                            {selectedCharacter.traits && selectedCharacter.traits.length > 0 && (
                                <div style={{ marginBottom: '16px' }}>
                                    <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '4px' }}>특징</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        {selectedCharacter.traits.map((trait: string, i: number) => (
                                            <span key={i} style={{
                                                fontSize: '0.8rem',
                                                padding: '4px 10px',
                                                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                                                color: '#4F46E5',
                                                borderRadius: '6px',
                                                fontWeight: '500'
                                            }}>
                                                {trait}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: '#666', marginTop: '24px', borderTop: '1px solid #eee', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <strong>첫 등장:</strong>
                                    <button
                                        onClick={() => scrollToScene(selectedCharacter.first_appearance, selectedCharacter.name)}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            color: '#4F46E5',
                                            fontWeight: 'bold',
                                            cursor: 'pointer',
                                            textDecoration: 'underline',
                                            padding: 0,
                                            fontSize: 'inherit'
                                        }}
                                    >
                                        {selectedCharacter.first_appearance + 1}씬
                                    </button>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <strong>총 등장:</strong> {selectedCharacter.appearance_count}회
                                        {(selectedCharacter.appearances && selectedCharacter.appearances.length > 0) && (
                                            <button
                                                onClick={() => setIsAppearancesExpanded(!isAppearancesExpanded)}
                                                style={{
                                                    background: 'none',
                                                    border: '1px solid #e2e8f0',
                                                    borderRadius: '4px',
                                                    cursor: 'pointer',
                                                    padding: '2px 6px',
                                                    fontSize: '0.8rem',
                                                    color: '#666',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px'
                                                }}
                                            >
                                                {isAppearancesExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                                {isAppearancesExpanded ? '접기' : '모두 보기'}
                                            </button>
                                        )}
                                    </div>

                                    {isAppearancesExpanded && selectedCharacter.appearances && (
                                        <div style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '6px',
                                            marginTop: '10px',
                                            maxHeight: '150px',
                                            overflowY: 'auto',
                                            width: '100%',
                                            padding: '4px'
                                        }}>
                                            {selectedCharacter.appearances.map((sceneIdx: number) => (
                                                <button
                                                    key={sceneIdx}
                                                    onClick={() => scrollToScene(sceneIdx, selectedCharacter.name)}
                                                    style={{
                                                        background: '#f1f5f9',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        color: '#475569',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px'
                                                    }}
                                                >
                                                    SCENE {sceneIdx + 1}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Item Detail Modal */}
            {
                selectedItem && (
                    <div
                        className="modal-overlay"
                        onClick={() => setSelectedItem(null)}
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: 'rgba(0,0,0,0.5)',
                            zIndex: 1000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <div
                            className="modal-content"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                backgroundColor: 'var(--bg-card, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--text-primary, #333)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{selectedItem.name}</h2>
                                <button
                                    onClick={() => setSelectedItem(null)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                                >
                                    <Package size={20} />
                                </button>
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '4px' }}>설명</div>
                                <p style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0 }}>
                                    {selectedItem.description || "상세 설명이 없습니다."}
                                </p>
                            </div>

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: '#666', marginTop: '24px', borderTop: '1px solid #eee', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <strong>첫 등장:</strong>
                                        <button
                                            onClick={() => scrollToScene(selectedItem.first_appearance, selectedItem.name)}
                                            style={{
                                                background: 'none',
                                                border: 'none',
                                                color: '#4F46E5',
                                                fontWeight: 'bold',
                                                cursor: 'pointer',
                                                textDecoration: 'underline',
                                                padding: 0,
                                                fontSize: 'inherit'
                                            }}
                                        >
                                            {selectedItem.first_appearance + 1}씬
                                        </button>
                                    </div>
                                    {selectedItem.appearance_count > 0 && (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                                            <strong>총 등장:</strong> {selectedItem.appearance_count}회
                                            {(selectedItem.appearances && selectedItem.appearances.length > 0) && (
                                                <button
                                                    onClick={() => setIsItemAppearancesExpanded(!isItemAppearancesExpanded)}
                                                    style={{
                                                        background: 'none',
                                                        border: '1px solid #e2e8f0',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        padding: '2px 6px',
                                                        fontSize: '0.8rem',
                                                        color: '#666',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px'
                                                    }}
                                                >
                                                    {isItemAppearancesExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                                    {isItemAppearancesExpanded ? '접기' : '모두 보기'}
                                                </button>
                                            )}
                                        </div>
                                    )}

                                    {isItemAppearancesExpanded && selectedItem.appearances && (
                                        <div style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '6px',
                                            marginTop: '10px',
                                            maxHeight: '150px',
                                            overflowY: 'auto',
                                            width: '100%',
                                            padding: '4px'
                                        }}>
                                            {selectedItem.appearances.map((sceneIdx: number) => (
                                                <button
                                                    key={sceneIdx}
                                                    onClick={() => scrollToScene(sceneIdx, selectedItem.name)}
                                                    style={{
                                                        background: '#f1f5f9',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        color: '#475569',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px'
                                                    }}
                                                >
                                                    SCENE {sceneIdx + 1}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Location Detail Modal */}
            {
                selectedLocation && (
                    <div
                        className="modal-overlay"
                        onClick={() => setSelectedLocation(null)}
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: 'rgba(0,0,0,0.5)',
                            zIndex: 1000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <div
                            className="modal-content"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                backgroundColor: 'var(--bg-card, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--text-primary, #333)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{selectedLocation.name}</h2>
                                <button
                                    onClick={() => setSelectedLocation(null)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                                >
                                    <MapPin size={20} />
                                </button>
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '4px' }}>설명</div>
                                <p style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0 }}>
                                    {selectedLocation.description || "상세 설명이 없습니다."}
                                </p>
                            </div>

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: '#666', marginTop: '24px', borderTop: '1px solid #eee', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <strong>총 등장:</strong> {selectedLocation.appearance_count || (selectedLocation.scenes ? selectedLocation.scenes.length : 0)}회
                                        {(selectedLocation.scenes && selectedLocation.scenes.length > 0) && (
                                            <button
                                                onClick={() => setIsLocationAppearancesExpanded(!isLocationAppearancesExpanded)}
                                                style={{
                                                    background: 'none',
                                                    border: '1px solid #e2e8f0',
                                                    borderRadius: '4px',
                                                    cursor: 'pointer',
                                                    padding: '2px 6px',
                                                    fontSize: '0.8rem',
                                                    color: '#666',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px'
                                                }}
                                            >
                                                {isLocationAppearancesExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                                {isLocationAppearancesExpanded ? '접기' : '모두 보기'}
                                            </button>
                                        )}
                                    </div>

                                    {isLocationAppearancesExpanded && selectedLocation.scenes && (
                                        <div style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '6px',
                                            marginTop: '10px',
                                            maxHeight: '150px',
                                            overflowY: 'auto',
                                            width: '100%',
                                            padding: '4px'
                                        }}>
                                            {selectedLocation.scenes.map((sceneIdx: number) => (
                                                <button
                                                    key={sceneIdx}
                                                    onClick={() => scrollToScene(sceneIdx)}
                                                    style={{
                                                        background: '#f1f5f9',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        color: '#475569',
                                                        cursor: 'pointer',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px'
                                                    }}
                                                >
                                                    SCENE {sceneIdx + 1}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Timeline Detail Modal */}
            {/* Key Event Detail Modal */}
            {
                selectedKeyEvent && (
                    <div
                        className="modal-overlay"
                        onClick={() => setSelectedKeyEvent(null)}
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: 'rgba(0,0,0,0.5)',
                            zIndex: 1000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <div
                            className="modal-content"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                backgroundColor: 'var(--bg-card, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--text-primary, #333)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0, lineHeight: 1.4 }}>
                                    {selectedKeyEvent.summary}
                                </h2>
                                <button
                                    onClick={() => setSelectedKeyEvent(null)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                                >
                                    <Clock size={20} />
                                </button>
                            </div>

                            <div style={{ marginBottom: '24px' }}>
                                {selectedKeyEvent.importance && (
                                    <div style={{
                                        display: 'inline-block',
                                        padding: '4px 8px',
                                        backgroundColor: '#f1f5f9',
                                        borderRadius: '4px',
                                        fontSize: '0.875rem',
                                        fontWeight: '500',
                                        color: '#475569',
                                        marginTop: '8px'
                                    }}>
                                        중요도: {selectedKeyEvent.importance}
                                    </div>
                                )}
                            </div>

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: '#666', marginTop: '16px', borderTop: '1px solid #eee', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
                                    <button
                                        onClick={() => scrollToScene(selectedKeyEvent.scene_index)}
                                        style={{
                                            width: '100%',
                                            background: '#4F46E5',
                                            border: 'none',
                                            borderRadius: '6px',
                                            padding: '10px 16px',
                                            fontSize: '0.95rem',
                                            fontWeight: '600',
                                            color: '#ffffff',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            gap: '8px',
                                            transition: 'background 0.2s'
                                        }}
                                    >
                                        <span>해당 씬으로 이동 ({selectedKeyEvent.scene_index + 1}씬)</span>
                                        <ChevronRight size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Generic Extra Item Detail Modal */}
            {
                selectedExtraItem && (
                    <div
                        className="modal-overlay"
                        onClick={() => setSelectedExtraItem(null)}
                        style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            backgroundColor: 'rgba(0,0,0,0.5)',
                            zIndex: 1000,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <div
                            className="modal-content"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                                backgroundColor: 'var(--bg-card, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--text-primary, #333)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>{selectedExtraItem.item.name || selectedExtraItem.item.title || "Detail"}</h2>
                                <button
                                    onClick={() => setSelectedExtraItem(null)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                                >
                                    <Package size={20} />
                                </button>
                            </div>

                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '4px' }}>{selectedExtraItem.title.toUpperCase()}</div>
                                <div style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0, maxHeight: '300px', overflowY: 'auto' }}>
                                    {selectedExtraItem.item.description || selectedExtraItem.item.summary || (
                                        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem', backgroundColor: '#f1f5f9', padding: '8px', borderRadius: '4px' }}>
                                            {JSON.stringify(selectedExtraItem.item, null, 2)}
                                        </pre>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* 설정 파괴 분석 결과 모달 */}
            <AnalysisResultModal
                isOpen={isAnalysisModalOpen}
                onClose={() => setIsAnalysisModalOpen(false)}
                result={analysisResult}
                isLoading={isAnalysisLoading}
                onNavigate={handleNavigateToQuote}
            />

            {/* Floating Menu - Settings, Analysis, Chatbot */}
            <FloatingMenu
                onNavigateToScene={scrollToScene}
                onCheckConsistency={handleCheckConsistency}
                onCheckPlotHoles={() => alert("스토리의 개연성과 플롯홀을 분석합니다...")}
                onOpenDictionary={() => alert("AI 어휘 사전 기능을 활성화합니다. 본문의 단어를 드래그해보세요.")}
                novelId={novelId}
                chapterId={chapterId}
                mode={mode}
            />
            {/* Settings Modal */}
            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
            />
        </div >
    );
}
