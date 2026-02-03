import { ArrowLeft, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Users, Package, Clock, Save, MapPin, X, FileText } from 'lucide-react';
import { useState, useEffect } from 'react';
import { FloatingMenu } from './FloatingMenu';
import { ThemeToggle } from './ThemeToggle';
import { getChapter, updateChapter, getChapterBible, BibleData, checkConsistency } from '../api/novel';

interface ChapterDetailProps {
    fileName: string;
    onBack: () => void;
    novelId?: number;
    chapterId?: number;
}

export function ChapterDetail({ fileName, onBack, novelId, chapterId }: ChapterDetailProps) {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isCharactersOpen, setIsCharactersOpen] = useState(true);
    const [isItemsOpen, setIsItemsOpen] = useState(false);
    const [isLocationsOpen, setIsLocationsOpen] = useState(false);
    const [isKeyEventsOpen, setIsKeyEventsOpen] = useState(false);

    const [content, setContent] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [initialLoadDone, setInitialLoadDone] = useState(false);

    const [bibleData, setBibleData] = useState<BibleData | null>(null);
    const [isBibleLoading, setIsBibleLoading] = useState(false);
    const [sceneTexts, setSceneTexts] = useState<string[]>([]);
    const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
    const [analysisReport, setAnalysisReport] = useState<string | null>(null);
    const [lastAnalyzedText, setLastAnalyzedText] = useState<string>("");

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

    const loadChapterContent = async () => {
        if (!novelId || !chapterId) {
            return;
        }
        setIsLoading(true);
        try {
            const chapter = await getChapter(novelId, chapterId);
            setContent(chapter.content);
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
                setSceneTexts(bible.scenes.map(s => s.original_text.trim()));
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
            await updateChapter(novelId, chapterId, { content: finalContent });
            alert("저장되었습니다.");
        } catch (error) {
            console.error("❌ 저장 실패 상세 오류:", error);
            alert("저장에 실패했습니다. 터미널 및 브라우저 콘솔 로그를 확인해주세요.");
        } finally {
            setIsSaving(false);
        }
    };

    const [selectedCharacter, setSelectedCharacter] = useState<any | null>(null);
    const [selectedItem, setSelectedItem] = useState<any | null>(null);
    const [selectedKeyEvent, setSelectedKeyEvent] = useState<any | null>(null);
    const [selectedExtraItem, setSelectedExtraItem] = useState<{ title: string, item: any } | null>(null);
    const [selectedLocation, setSelectedLocation] = useState<any | null>(null);
    const [extraSectionStates, setExtraSectionStates] = useState<Record<string, boolean>>({});
    const [isAppearancesExpanded, setIsAppearancesExpanded] = useState(false);
    const [isItemAppearancesExpanded, setIsItemAppearancesExpanded] = useState(false);
    const [isLocationAppearancesExpanded, setIsLocationAppearancesExpanded] = useState(false);

    const scrollToScene = (index: number) => {
        // Close all modals first
        setSelectedCharacter(null);
        setSelectedItem(null);
        setSelectedKeyEvent(null);
        setSelectedExtraItem(null);
        setSelectedLocation(null);
        setIsAppearancesExpanded(false);
        setIsItemAppearancesExpanded(false);
        setIsLocationAppearancesExpanded(false);

        // Wait for state updates and then scroll
        setTimeout(() => {
            const element = document.getElementById(`scene-block-${index}`);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Optional: Highlight effect
                element.style.transition = 'background-color 0.5s';
                element.style.backgroundColor = 'rgba(79, 70, 229, 0.1)';
                setTimeout(() => {
                    element.style.backgroundColor = 'transparent';
                }, 1000);
            }
        }, 100);
    };

    const handleCheckConsistency = async () => {
        if (!novelId) return;

        // 현재 에디터 내용 가져오기 (씬 분할 모드면 씬 합침, 아니면 content)
        const currentText = sceneTexts.length > 0
            ? sceneTexts.join("\n\n")
            : content;

        if (!currentText.trim()) {
            alert("분석할 내용이 없습니다.");
            return;
        }

        setLastAnalyzedText(currentText);
        setIsAnalysisLoading(true);
        try {
            const res = await checkConsistency(novelId, currentText);
            setAnalysisReport(res.report);
            if ((res as any).target_sentence) {
                setLastAnalyzedText((res as any).target_sentence);
            } else {
                setLastAnalyzedText(currentText);
            }
        } catch (error) {
            alert("분석 중 오류가 발생했습니다.");
            console.error(error);
        } finally {
            setIsAnalysisLoading(false);
        }
    };

    const navigateToAnalyzedText = () => {
        if (!lastAnalyzedText) return;

        const target = lastAnalyzedText.trim();
        const normalize = (text: string) => text.replace(/[\s\n\t\r.,!?-]/g, '');
        const normalizedTarget = normalize(target);

        console.log(`🔎 검색어 정규화: "${normalizedTarget}"`);

        // 1. Find which scene contains the text (using fuzzy normalization)
        let index = sceneTexts.findIndex(s => {
            const normalizedScene = normalize(s);
            return normalizedScene.includes(normalizedTarget);
        });

        if (index !== -1) {
            console.log(`🎯 문제의 문장을 씬 ${index + 1}에서 발견했습니다.`);

            // Scroll to the scene block
            const element = document.getElementById(`scene-block-${index}`);
            const textarea = element?.querySelector('textarea') as HTMLTextAreaElement;

            if (element && textarea) {
                element.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Focus and Precise Selection
                setTimeout(() => {
                    textarea.focus();
                    const content = textarea.value;

                    // 원본에서 위치 찾기
                    let startPos = content.indexOf(target);
                    let matchLen = target.length;

                    // 매칭 실패 시 부분 매칭 시도
                    if (startPos === -1 && target.length > 5) {
                        const startChunk = target.substring(0, 5);
                        startPos = content.indexOf(startChunk);
                    }

                    if (startPos !== -1) {
                        textarea.setSelectionRange(startPos, startPos + matchLen);

                        // 텍스트박스 내부 스크롤 (커서 위치로 이동)
                        const lineHeight = 24;
                        const charsPerLine = Math.floor(textarea.clientWidth / 10) || 40;
                        const lineNumber = Math.floor(startPos / charsPerLine);
                        textarea.scrollTop = lineNumber * lineHeight - (textarea.clientHeight / 3);

                        // Visual feedback highlight
                        element.style.transition = 'box-shadow 0.5s';
                        element.style.boxShadow = '0 0 25px rgba(79, 70, 229, 0.7)';
                        setTimeout(() => {
                            element.style.boxShadow = 'none';
                        }, 3000);
                    }
                }, 600);
            }
            setAnalysisReport(null);
        } else {
            console.log("❌ 문제의 문장을 찾지 못해 에디터 상단으로 이동합니다.");
            const container = document.querySelector('.scenes-container') || document.querySelector('.novel-text-editor');
            if (container) {
                container.scrollTo({ top: 0, behavior: 'smooth' });
                setAnalysisReport(null);
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

    const locations = bibleData?.locations && bibleData.locations.length > 0
        ? bibleData.locations
        : [
            { name: '강둑', description: '언니와 함께 앉아있던 곳', scenes: [0] },
            { name: '토끼 굴', description: '토끼가 들어간 긴 굴', scenes: [2] },
        ];

    // ... (rest of items/timeline)

    return (
        <div className="chapter-detail-container">
            {/* Header */}
            {/* ... (Header code remains same) ... */}
            <div className="chapter-detail-header">
                <button className="back-button" onClick={onBack}>
                    <ArrowLeft size={24} />
                </button>
                <div style={{ flex: 1 }}>
                    <h1 className="chapter-detail-title">{fileName}</h1>
                </div>
                {novelId && chapterId && (
                    <button
                        className="save-button"
                        onClick={handleSave}
                        disabled={isSaving}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '8px 16px',
                            backgroundColor: '#4F46E5',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: isSaving ? 'wait' : 'pointer'
                        }}
                    >
                        <Save size={18} />
                        {isSaving ? '저장 중...' : '저장'}
                    </button>
                )}
            </div>

            {/* Main Layout */}
            <div className="chapter-detail-layout">
                {/* Sidebar */}
                <div className={`dictionary-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
                    {/* Characters Section */}
                    <div className="sidebar-section">
                        <button
                            className="section-header"
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
                            className="section-header"
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
                            className="section-header"
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
                            className="section-header"
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
                                    className="section-header"
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

                {/* Main Text Area */}
                <div className="text-area" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div className="text-content" style={{ flex: 1, padding: 0, height: '100%' }}>
                        {isLoading ? (
                            <div style={{ padding: '20px', textAlign: 'center' }}>로딩 중...</div>
                        ) : sceneTexts.length > 0 ? (
                            <div className="scenes-container" style={{ height: '100%', overflowY: 'auto', padding: '20px' }}>
                                {sceneTexts.map((text, index) => (
                                    <div
                                        key={index}
                                        id={`scene-block-${index}`}
                                        className="scene-block"
                                        style={{ marginBottom: '30px', position: 'relative' }}
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
                                        <textarea
                                            value={text}
                                            ref={(el) => {
                                                if (el) adjustTextareaHeight(el);
                                            }}
                                            onInput={(e) => adjustTextareaHeight(e.currentTarget)}
                                            onChange={(e) => {
                                                const newScenes = [...sceneTexts];
                                                newScenes[index] = e.target.value;
                                                setSceneTexts(newScenes);
                                            }}
                                            style={{
                                                width: '100%',
                                                minHeight: '150px',
                                                height: 'auto',
                                                border: '1px solid #e2e8f0',
                                                resize: 'none',
                                                padding: '20px',
                                                paddingTop: '25px',
                                                fontSize: '1.1rem',
                                                lineHeight: '1.6',
                                                outline: 'none',
                                                backgroundColor: 'white',
                                                color: 'inherit',
                                                fontFamily: 'inherit',
                                                borderRadius: '8px',
                                                boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                                                overflow: 'hidden'
                                            }}
                                            spellCheck={false}
                                        />
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <textarea
                                className="novel-text-editor"
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                style={{
                                    width: '100%',
                                    height: '100%',
                                    border: 'none',
                                    resize: 'none',
                                    padding: '40px',
                                    fontSize: '1.1rem',
                                    lineHeight: '1.6',
                                    outline: 'none',
                                    backgroundColor: 'transparent',
                                    color: 'inherit',
                                    fontFamily: 'inherit'
                                }}
                                spellCheck={false}
                            />
                        )}
                    </div>
                </div>
            </div>

            {/* Character Detail Modal */}
            {selectedCharacter && (
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
                                    onClick={() => scrollToScene(selectedCharacter.first_appearance)}
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
            )}

            {/* Item Detail Modal */}
            {selectedItem && (
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
                                        onClick={() => scrollToScene(selectedItem.first_appearance)}
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
            )}

            {/* Location Detail Modal */}
            {selectedLocation && (
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
            )}

            {/* Timeline Detail Modal */}
            {/* Key Event Detail Modal */}
            {selectedKeyEvent && (
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
            )}

            {/* Generic Extra Item Detail Modal */}
            {selectedExtraItem && (
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
            )}

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Floating Menu - Settings, Analysis, Chatbot */}
            <FloatingMenu
                onNavigateToScene={scrollToScene}
                onCheckConsistency={handleCheckConsistency}
            />

            {/* Analysis Loading Overlay */}
            {isAnalysisLoading && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.7)',
                    zIndex: 2000,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white'
                }}>
                    <div className="loader" style={{
                        border: '4px solid #f3f3f3',
                        borderTop: '4px solid #4F46E5',
                        borderRadius: '50%',
                        width: '40px',
                        height: '40px',
                        animation: 'spin 1s linear infinite',
                        marginBottom: '16px'
                    }}></div>
                    <style>{`
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    `}</style>
                    <p style={{ fontSize: '1.2rem', fontWeight: '500' }}>설정 오류 분석 중...</p>
                    <p style={{ fontSize: '0.9rem', opacity: 0.8, marginTop: '8px' }}>줄거리와 바이블 설정을 비교하고 있습니다.</p>
                </div>
            )}

            {/* Analysis Result Modal */}
            {analysisReport && (
                <div
                    className="modal-overlay"
                    onClick={() => setAnalysisReport(null)}
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
                            width: '800px',
                            maxWidth: '90%',
                            maxHeight: '80vh',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                            color: 'var(--text-primary, #333)',
                            overflowY: 'auto'
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '16px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                <div style={{ backgroundColor: '#4F46E5', color: 'white', padding: '6px', borderRadius: '6px' }}>
                                    <FileText size={24} />
                                </div>
                                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0 }}>설정파괴 분석 레포트</h2>
                            </div>
                            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                                <button
                                    onClick={navigateToAnalyzedText}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '6px 12px',
                                        backgroundColor: '#EEF2FF',
                                        color: '#4F46E5',
                                        border: '1px solid #C7D2FE',
                                        borderRadius: '6px',
                                        fontSize: '0.9rem',
                                        fontWeight: '600',
                                        cursor: 'pointer'
                                    }}
                                    title="해당 문장 위치로 이동"
                                >
                                    <ArrowLeft size={16} />
                                    위치 이동
                                </button>
                                <button
                                    onClick={() => setAnalysisReport(null)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                                >
                                    <X size={24} />
                                </button>
                            </div>
                        </div>

                        <div className="report-content" style={{
                            lineHeight: '1.8',
                            fontSize: '1.05rem',
                            whiteSpace: 'pre-wrap',
                            backgroundColor: '#f8fafc',
                            padding: '20px',
                            borderRadius: '8px',
                            border: '1px solid #e2e8f0'
                        }}>
                            {analysisReport}
                        </div>

                        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end' }}>
                            <button
                                onClick={() => setAnalysisReport(null)}
                                style={{
                                    padding: '10px 20px',
                                    backgroundColor: '#4F46E5',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    fontWeight: 'bold',
                                    cursor: 'pointer'
                                }}
                            >
                                확인 완료
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
