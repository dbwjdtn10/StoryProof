import { ArrowLeft, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Users, Package, Clock, Save, MapPin } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Editor } from '@tiptap/react';
import { NovelEditor } from './NovelEditor';
import { AuthorToolbar } from './AuthorToolbar';
import { ReaderToolbar } from './ReaderToolbar';
import { FloatingMenu } from './FloatingMenu';
import { ThemeToggle } from './ThemeToggle';
import { getChapter, updateChapter, getChapterBible, reanalyzeChapter, getStoryboardStatus, BibleData, Character, Item, Location } from '../api/novel';
import { AnalysisSidebar, AnalysisResult } from './AnalysisSidebar';
import { PredictionSidebar, Message } from './predictions/PredictionSidebar';
import { requestPrediction, getPredictionTaskStatus } from '../api/prediction';
import { requestConsistencyCheck, getTaskResult } from '../api/analysis';
import { toast } from 'sonner';
import { generateImage } from '../api/images';
import '../novel-toolbar.css';

interface ChapterDetailProps {
    fileName: string;
    onBack: () => void;
    novelId?: number;
    chapterId?: number;
    mode?: 'reader' | 'writer';
    onOpenCharacterChat?: () => void;
}

export function ChapterDetail({ fileName, onBack, novelId, chapterId, mode = 'writer', onOpenCharacterChat }: ChapterDetailProps) {
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

    const [chapterStatus, setChapterStatus] = useState<'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | undefined>(undefined);

    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [isImageGenerating, setIsImageGenerating] = useState(false);

    // Story Prediction State
    const [isPredictionSidebarOpen, setIsPredictionSidebarOpen] = useState(false);
    const [chatMessages, setChatMessages] = useState<Message[]>([]);
    const [isPredictionLoading, setIsPredictionLoading] = useState(false);

    // Highlight State
    const [highlightData, setHighlightData] = useState<{
        sceneIndex: number;
        text: string;
        timestamp: number;
    } | null>(null);

    // Tiptap Editor State
    const [activeEditor, setActiveEditor] = useState<Editor | null>(null);

    // Reader Mode Settings
    const [readerSettings, setReaderSettings] = useState(() => {
        const saved = localStorage.getItem('reader-settings');
        return saved ? JSON.parse(saved) : {
            fontSize: 18,
            lineHeight: 2.0,
            paragraphSpacing: 40,
            contentWidth: 80,
            fontFamily: 'Noto Sans KR',
            theme: 'light'
        };
    });

    useEffect(() => {
        localStorage.setItem('reader-settings', JSON.stringify(readerSettings));

        // Apply theme to document for reader mode
        if (mode === 'reader') {
            document.documentElement.setAttribute('data-reader-theme', readerSettings.theme);
        } else {
            document.documentElement.removeAttribute('data-reader-theme');
        }
    }, [readerSettings, mode]);

    // Clear highlight after 15 seconds
    useEffect(() => {
        if (highlightData) {
            const timer = setTimeout(() => {
                setHighlightData(null);
            }, 15000);
            return () => clearTimeout(timer);
        }
    }, [highlightData]);

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
                    const statusData = await getStoryboardStatus(novelId, chapterId);
                    const currentStatus = statusData.status?.toUpperCase() || '';

                    if (currentStatus === 'COMPLETED' || currentStatus === 'FAILED') {
                        setChapterStatus(currentStatus as any);
                        setIsAnalyzing(false);
                        if (currentStatus === 'COMPLETED') {
                            toast.success("분석이 완료되었습니다! 데이터를 새로고침합니다.");
                            loadChapterContent();
                            loadBibleData();
                        } else {
                            toast.error(`분석 실패: ${statusData.message || '알 수 없는 오류'}`);
                        }
                    }
                } catch (error) {
                    console.error("Status check failed", error);
                }
            }, 3000);
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
            toast.error("소설 내용을 불러오는데 실패했습니다.");
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
                // 줄바꿈 보존: 원본 텍스트 그대로 사용
                setSceneTexts(bible.scenes.map(s =>
                    s.original_text.trim()
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
            await updateChapter(novelId, chapterId, { content: finalContent });
            toast.success("저장되었습니다.");
        } catch (error) {
            toast.error("저장에 실패했습니다.");
        } finally {
            setIsSaving(false);
        }
    };

    const [selectedCharacter, setSelectedCharacter] = useState<any | null>(null);
    const [selectedItem, setSelectedItem] = useState<any | null>(null);
    const [selectedKeyEvent, setSelectedKeyEvent] = useState<any | null>(null);
    const [selectedExtraItem, setSelectedExtraItem] = useState<{ title: string, item: any } | null>(null);

    // 설정 파괴 분석 상태
    const [isAnalysisSidebarOpen, setIsAnalysisSidebarOpen] = useState(false);
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
        setIsAnalysisSidebarOpen(true);
        setIsPredictionSidebarOpen(false); // Mutual exclusion
        setIsAnalysisLoading(true);
        setAnalysisResult(null);

        try {
            // 현재 모든 씬의 텍스트를 합쳐서 분석 요청 (씬 모드 vs 에디터 모드)
            const allText = sceneTexts.length > 0
                ? sceneTexts.join('\n\n')
                : content;

            const { task_id } = await requestConsistencyCheck({
                novel_id: novelId!,
                chapter_id: chapterId,
                text: allText
            });

            // 폴링 시작
            const intervalId = setInterval(async () => {
                try {
                    const data = await getTaskResult(task_id);

                    if (data.status === "COMPLETED") {
                        clearInterval(intervalId);
                        setAnalysisResult(data.result as AnalysisResult);
                        setIsAnalysisLoading(false);
                        toast.success("분석이 완료되었습니다.");
                    } else if (data.status === "FAILED") {
                        clearInterval(intervalId);
                        setIsAnalysisLoading(false);
                        setAnalysisResult({ status: "실패", message: data.error || "분석 작업이 실패했습니다." });
                        toast.error("분석 중 오류가 발생했습니다.");
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                    clearInterval(intervalId);
                    setIsAnalysisLoading(false);
                    setAnalysisResult({ status: "오류", message: "상태 확인 중 서버 통신 오류가 발생했습니다." });
                }
            }, 2000);

            // 컴포넌트 언마운트 시 인터벌 클리어를 위해 (실제로는 state나 ref로 관리하는게 좋지만 우선 이 로직 내에서 처리)
            // 작업 중 중단 방지 등을 고려해 setInterval의 수명주기를 관리함
        } catch (error) {
            console.error("Analysis error:", error);
            setAnalysisResult({ status: "오류 발생", message: "서버와 통신 중 오류가 발생했습니다." });
            setIsAnalysisLoading(false);
        }
    };

    const handlePredictionSidebarOpen = () => {
        setIsPredictionSidebarOpen(true);
        setIsAnalysisSidebarOpen(false); // Mutual exclusion
    };

    const handleSendMessage = async (inputMessage: string) => {
        if (!novelId || !inputMessage.trim()) return;

        const newUserMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputMessage
        };

        setChatMessages(prev => [...prev, newUserMsg]);
        setIsPredictionLoading(true);

        try {
            const { task_id } = await requestPrediction(novelId, inputMessage);

            // Poll for result
            const pollInterval = setInterval(async () => {
                try {
                    const data = await getPredictionTaskStatus(task_id);

                    if (data.status === "COMPLETED") {
                        clearInterval(pollInterval);
                        // @ts-ignore
                        const resultText = data.result.prediction || data.result.text || (typeof data.result === 'string' ? data.result : JSON.stringify(data.result));

                        const newBotMsg: Message = {
                            id: (Date.now() + 1).toString(),
                            role: 'assistant',
                            content: resultText
                        };

                        setChatMessages(prev => [...prev, newBotMsg]);
                        setIsPredictionLoading(false);

                        if (Notification.permission === "granted" && document.hidden) {
                            new Notification("StoryProof 답변 도착", {
                                body: "챗봇이 응답했습니다.",
                                icon: "/favicon.ico"
                            });
                        }

                    } else if (data.status === "FAILED") {
                        clearInterval(pollInterval);
                        setIsPredictionLoading(false);
                        toast.error("답변 생성 중 오류가 발생했습니다.");
                    }
                } catch (e) {
                    // Continue polling
                }
            }, 2000);

        } catch (error) {
            setIsPredictionLoading(false);
            toast.error("서버 요청에 실패했습니다.");
        }
    };

    const handlePredictStoryTrigger = () => {
        handlePredictionSidebarOpen();
    };

    const handleNavigateToQuote = (quote: string) => {
        if (!quote) return;

        // 정규화 함수: 모든 특수문자, 공백, 줄바꿈을 제거하여 비교용으로 만듦
        const superNormalize = (str: string) => str.replace(/[^a-zA-Z0-9가-힣]/g, '');
        const targetClean = superNormalize(quote);

        console.log(`[Navigation] Searching for quote: "${quote}"`);
        console.log(`[Navigation] Cleaned target: "${targetClean}"`);

        // 1. Scene Mode Navigation (sceneTexts exists)
        if (sceneTexts.length > 0) {
            // 정밀 검색: 모든 씬을 돌면서 정규화된 텍스트 포함 여부 확인
            let foundIndex = -1;

            // 우선 정확한 포함 관계 확인
            foundIndex = sceneTexts.findIndex(s => superNormalize(s).includes(targetClean));

            // 만약 못 찾았다면, 앞부분과 뒷부분만으로 부분 매칭 시도 (LLM 적은 생략 가능성 대비)
            if (foundIndex === -1 && targetClean.length > 40) {
                const head = targetClean.substring(0, 30);
                const tail = targetClean.substring(targetClean.length - 30);
                console.log(`[Navigation] Fallback partial search: head("${head}"), tail("${tail}")`);
                foundIndex = sceneTexts.findIndex(s => {
                    const cleanS = superNormalize(s);
                    return cleanS.includes(head) && cleanS.includes(tail);
                });
            }

            if (foundIndex !== -1) {
                console.log(`[Navigation] Found in scene ${foundIndex + 1}`);
                scrollToScene(foundIndex, quote);
            } else {
                console.warn(`[Navigation] Quote not found in any scene. Sample scene 1 start: ${superNormalize(sceneTexts[0]).substring(0, 50)}`);
                toast.warning('해당 문장을 본문에서 찾을 수 없습니다. (문장이 일부 다르거나 다른 회차의 내용일 수 있습니다)');
            }
        }
        // 2. Single Textarea Mode (content)
        else {
            const textArea = document.querySelector('.novel-text-editor') as HTMLTextAreaElement;
            if (textArea && content) {
                const cleanContent = superNormalize(content);
                const cleanPos = cleanContent.indexOf(targetClean);

                if (cleanPos !== -1) {
                    // 대략적인 위치 찾기 (정확한 pos를 알기 위해서는 역산이 필요하나, 
                    // 텍스트 영역이 크면 indexOf(quote)가 대부분 작동함)
                    const pos = content.indexOf(quote);
                    if (pos !== -1) {
                        textArea.focus();
                        textArea.setSelectionRange(pos, pos + quote.length);
                        const lines = content.substring(0, pos).split("\n").length;
                        textArea.scrollTop = (lines - 1) * 24;
                    } else {
                        // 정규화로는 찾았으나 원본에서 못 찾은 경우
                        toast.warning('문장을 찾았으나, 정확한 위치 선정이 어려워 이동이 제한됩니다.');
                    }
                } else {
                    toast.warning('해당 문장을 본문에서 찾을 수 없습니다.');
                }
            }
        }
    };

    const handleBookmark = () => {
        toast.info("책갈피 기능은 준비 중입니다.");
    };

    const handleHighlight = () => {
        if (!activeEditor) return;
        activeEditor.chain().focus().toggleHighlight().run();
    };

    const handleAddMemo = () => {
        toast.info("메모 기능은 준비 중입니다.");
    };

    const handleOpenSettings = () => {
        toast.info("환경설정 기능은 준비 중입니다.");
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
            toast.info("현재 분석이 진행 중입니다. 잠시만 기다려주세요.");
            return;
        }

        setIsAnalyzing(true);
        setChapterStatus('PROCESSING');
        try {
            await reanalyzeChapter(novelId, chapterId);
            toast.success("재분석 요청이 완료되었습니다. 백그라운드에서 분석이 진행됩니다.");
        } catch (error) {
            console.error(error);
            toast.error("재분석 요청 실패");
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
    const handleGenerateImage = async (type: 'character' | 'item' | 'location', entity: Character | Item | Location) => {
        if (!novelId || !chapterId) {
            toast.error("소설/챕터 정보가 없습니다.");
            return;
        }

        setIsImageGenerating(true);
        try {
            const result = await generateImage({
                novel_id: novelId,
                chapter_id: chapterId,
                entity_type: type,
                entity_name: entity.name,
                description: entity.description || entity.name
            });

            // Update local state to show image immediately
            const newImage = result.image_url; // relative path from backend

            // Function to update the specific entity in a list
            const updateEntityInList = (list: any[]) => {
                return list.map(item => item.name === entity.name ? { ...item, image: newImage } : item);
            };

            setBibleData(prev => {
                if (!prev) return null;
                const newData = { ...prev };
                if (type === 'character') newData.characters = updateEntityInList(newData.characters);
                if (type === 'item') newData.items = updateEntityInList(newData.items);
                if (type === 'location') newData.locations = updateEntityInList(newData.locations);
                return newData;
            });

            // Update currently selected item if it's the one we generated for
            if (type === 'character' && selectedCharacter?.name === entity.name) {
                setSelectedCharacter((prev: Character | null) => prev ? { ...prev, image: newImage } : null);
            }
            if (type === 'item' && selectedItem?.name === entity.name) {
                setSelectedItem((prev: Item | null) => prev ? { ...prev, image: newImage } : null);
            }
            if (type === 'location' && selectedLocation?.name === entity.name) {
                setSelectedLocation((prev: Location | null) => prev ? { ...prev, image: newImage } : null);
            }

            toast.success("이미지가 생성되었습니다!");
        } catch (error) {
            console.error("Image generation failed:", error);
            toast.error("이미지 생성에 실패했습니다.");
        } finally {
            setIsImageGenerating(false);
        }
    };

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
                position: 'sticky',
                top: 0,
                zIndex: 10
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
                <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
                    <h1 className="chapter-detail-title" style={{
                        fontSize: '1.25rem',
                        fontWeight: 600,
                        color: '#1F2937',
                        margin: 0
                    }}>{fileName}</h1>
                    <span style={{
                        marginLeft: '12px',
                        padding: '4px 12px',
                        borderRadius: '9999px',
                        fontSize: '12px',
                        fontWeight: 600,
                        backgroundColor: mode === 'reader' ? '#E0F2FE' : '#EEF2FF',
                        color: mode === 'reader' ? '#0369A1' : '#4F46E5',
                        whiteSpace: 'nowrap'
                    }}>
                        {mode === 'reader' ? '📖 독자 모드' : '✍️ 작가 모드'}
                    </span>
                </div>
                {novelId && chapterId && mode !== 'reader' && (
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            className="reanalyze-button"
                            onClick={handleReanalyze}
                            disabled={chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing}
                            title={(chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING') ? "분석 진행 중..." : "AI 재분석"}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '8px 16px',
                                backgroundColor: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? '#F3F4F6' : 'white',
                                color: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? '#9CA3AF' : '#4F46E5',
                                border: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? '1px solid #E5E7EB' : '1px solid #4F46E5',
                                borderRadius: '6px',
                                cursor: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? 'not-allowed' : 'pointer',
                                fontSize: '0.9rem',
                                fontWeight: 500
                            }}
                        >
                            <Clock size={16} className={(chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? "spin-animation" : ""} />
                            {(chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? '분석 중...' : '재분석'}
                        </button>
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
                                cursor: isSaving ? 'wait' : 'pointer',
                                fontSize: '0.9rem',
                                fontWeight: 500
                            }}
                        >
                            <Save size={18} />
                            {isSaving ? '저장 중...' : '저장'}
                        </button>
                    </div>
                )}
            </div>

            {/* Author/Reader Toolbar */}
            {mode === 'reader' ? (
                <ReaderToolbar
                    editor={activeEditor}
                    readerSettings={readerSettings}
                    onSettingsChange={setReaderSettings}
                    onBookmark={handleBookmark}
                    onHighlight={handleHighlight}
                    onAddMemo={handleAddMemo}
                />
            ) : (
                <AuthorToolbar
                    editor={activeEditor}
                    onOpenSettings={() => {
                        handleOpenSettings();
                    }}
                />
            )}


            {/* Main Layout */}
            <div className="chapter-detail-layout">
                {/* Sidebar */}
                <div className={`dictionary-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
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

                {/* Main Text Area */}
                <div className="text-area" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    <div className="text-content" style={{ flex: 1, padding: 0, height: '100%' }}>
                        {isLoading ? (
                            <div style={{ padding: '20px', textAlign: 'center' }}>로딩 중...</div>
                        ) : sceneTexts.length > 0 ? (
                            <div
                                className="scenes-container"
                                style={{
                                    height: '100%',
                                    overflowY: 'auto',
                                    padding: '20px',
                                    backgroundColor: mode === 'reader' ? 'var(--reader-bg, #ffffff)' : 'white'
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

                                        <div className="scene-content-wrapper" style={{
                                            maxWidth: mode === 'reader' ? `${readerSettings.contentWidth}%` : '100%',
                                            margin: mode === 'reader' ? '0 auto' : '0'
                                        }}>
                                            <NovelEditor
                                                content={text.replace(/\n/g, '<br>')}
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
                                                style={mode === 'reader' ? {
                                                    fontSize: `${readerSettings.fontSize}px`,
                                                    lineHeight: readerSettings.lineHeight,
                                                    fontFamily: readerSettings.fontFamily,
                                                    color: 'var(--text-primary)'
                                                } : undefined}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div style={{
                                maxWidth: mode === 'reader' ? `${readerSettings.contentWidth}%` : '100%',
                                margin: mode === 'reader' ? '0 auto' : '0',
                                height: '100%'
                            }}>
                                <NovelEditor
                                    content={content.replace(/\n/g, '<br>')}
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
                                    style={mode === 'reader' ? {
                                        fontSize: `${readerSettings.fontSize}px`,
                                        lineHeight: readerSettings.lineHeight,
                                        fontFamily: readerSettings.fontFamily,
                                        color: 'var(--text-primary)'
                                    } : undefined}
                                />
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

                            {/* Image Section */}
                            <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                {selectedCharacter.image ? (
                                    <img
                                        src={selectedCharacter.image}
                                        alt={selectedCharacter.name}
                                        style={{ width: '100%', maxHeight: '300px', objectFit: 'contain', borderRadius: '8px', marginBottom: '8px' }}
                                    />
                                ) : (
                                    <div style={{
                                        width: '100%',
                                        height: '200px',
                                        backgroundColor: '#f1f5f9',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#94a3b8',
                                        marginBottom: '8px'
                                    }}>
                                        이미지 없음
                                    </div>
                                )}
                                <button
                                    onClick={() => handleGenerateImage('character', selectedCharacter)}
                                    disabled={isImageGenerating}
                                    style={{
                                        padding: '8px 16px',
                                        backgroundColor: isImageGenerating ? '#cbd5e1' : '#4f46e5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: isImageGenerating ? 'not-allowed' : 'pointer',
                                        fontWeight: '500',
                                        fontSize: '0.9rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    {isImageGenerating ? '생성 중...' : (selectedCharacter.image ? '이미지 재생성' : '이미지 생성')}
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

                            {/* Image Section */}
                            <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                {selectedItem.image ? (
                                    <img
                                        src={selectedItem.image}
                                        alt={selectedItem.name}
                                        style={{ width: '100%', maxHeight: '300px', objectFit: 'contain', borderRadius: '8px', marginBottom: '8px' }}
                                    />
                                ) : (
                                    <div style={{
                                        width: '100%',
                                        height: '200px',
                                        backgroundColor: '#f1f5f9',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#94a3b8',
                                        marginBottom: '8px'
                                    }}>
                                        이미지 없음
                                    </div>
                                )}
                                <button
                                    onClick={() => handleGenerateImage('item', selectedItem)}
                                    disabled={isImageGenerating}
                                    style={{
                                        padding: '8px 16px',
                                        backgroundColor: isImageGenerating ? '#cbd5e1' : '#4f46e5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: isImageGenerating ? 'not-allowed' : 'pointer',
                                        fontWeight: '500',
                                        fontSize: '0.9rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    {isImageGenerating ? '생성 중...' : (selectedItem.image ? '이미지 재생성' : '이미지 생성')}
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

                            {/* Image Section */}
                            <div style={{ marginBottom: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                {selectedLocation.image ? (
                                    <img
                                        src={selectedLocation.image}
                                        alt={selectedLocation.name}
                                        style={{ width: '100%', maxHeight: '300px', objectFit: 'contain', borderRadius: '8px', marginBottom: '8px' }}
                                    />
                                ) : (
                                    <div style={{
                                        width: '100%',
                                        height: '200px',
                                        backgroundColor: '#f1f5f9',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#94a3b8',
                                        marginBottom: '8px'
                                    }}>
                                        이미지 없음
                                    </div>
                                )}
                                <button
                                    onClick={() => handleGenerateImage('location', selectedLocation)}
                                    disabled={isImageGenerating}
                                    style={{
                                        padding: '8px 16px',
                                        backgroundColor: isImageGenerating ? '#cbd5e1' : '#4f46e5',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: isImageGenerating ? 'not-allowed' : 'pointer',
                                        fontWeight: '500',
                                        fontSize: '0.9rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '8px'
                                    }}
                                >
                                    {isImageGenerating ? '생성 중...' : (selectedLocation.image ? '이미지 재생성' : '이미지 생성')}
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

            {/* 설정 파괴 분석 결과 사이드바 */}
            <AnalysisSidebar
                isOpen={isAnalysisSidebarOpen}
                onClose={() => setIsAnalysisSidebarOpen(false)}
                result={analysisResult}
                isLoading={isAnalysisLoading}
                onNavigateToQuote={handleNavigateToQuote}
            />

            {/* 스토리 예측 사이드바 */}
            <PredictionSidebar
                isOpen={isPredictionSidebarOpen}
                onClose={() => setIsPredictionSidebarOpen(false)}
                messages={chatMessages}
                onSendMessage={handleSendMessage}
                isLoading={isPredictionLoading}
                onClearChat={() => setChatMessages([])}
            />

            {/* Floating Menu - Settings, Analysis, Prediction, Chatbot */}
            <FloatingMenu
                onNavigateToScene={scrollToScene}
                onCheckConsistency={handleCheckConsistency}
                onPredictStory={handlePredictStoryTrigger}
                onOpenCharacterChat={onOpenCharacterChat}
                novelId={novelId}
                chapterId={chapterId}
                mode={mode}
            />
        </div>
    );
}
