import { ArrowLeft, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Users, Package, Clock, Save, MapPin, Search, Download, FileText, File as FileIcon, X, Link2 } from 'lucide-react';
import { useState, useEffect, useRef, useMemo } from 'react';
import { Editor } from '@tiptap/react';
import { NovelEditor } from './NovelEditor';
import { AuthorToolbar } from './AuthorToolbar';
import { ReaderToolbar } from './ReaderToolbar';
import { FloatingMenu } from './FloatingMenu';
import { ThemeToggle } from './ThemeToggle';
import { Settings } from './Settings';
import { getChapter, getChapters, getStoryboardStatus, updateChapter, getChapterBible, reanalyzeChapter, exportBible, exportChapter, BibleData, ChapterListItem, Character, Item, Location } from '../api/novel';
import { AnalysisSidebar, AnalysisResult } from './AnalysisSidebar';
import { RelationshipGraphModal } from './RelationshipGraph';
import { PredictionSidebar, Message } from './predictions/PredictionSidebar';
import { requestPrediction, getPredictionTaskStatus, getPredictionHistory, clearPredictionHistory } from '../api/prediction';
import { getCachedConsistency, requestConsistencyCheck, getTaskResult, requestChapterAnalysis, getCachedChapterAnalysis } from '../api/analysis';
import { toast } from 'sonner';
import { generateImage } from '../api/images';
import { useTheme } from '../contexts/ThemeContext';
import '../novel-toolbar.css';

interface ChapterDetailProps {
    fileName: string;
    onBack: () => void;
    novelId?: number;
    chapterId?: number;
    mode?: 'reader' | 'writer';
    onOpenCharacterChat?: () => void;
    onCloseCharacterChat?: () => void;
    onNavigateChapter?: (chapterId: number, title: string) => void;
    showCharacterChat?: boolean;
}

export function ChapterDetail({ fileName, onBack, novelId, chapterId, mode = 'writer', onOpenCharacterChat, onCloseCharacterChat, onNavigateChapter, showCharacterChat }: ChapterDetailProps) {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isCharactersOpen, setIsCharactersOpen] = useState(true);
    const [isItemsOpen, setIsItemsOpen] = useState(false);
    const [isLocationsOpen, setIsLocationsOpen] = useState(false);
    const [isKeyEventsOpen, setIsKeyEventsOpen] = useState(false);
    const [isRelationshipsOpen, setIsRelationshipsOpen] = useState(false);
    const [isRelGraphOpen, setIsRelGraphOpen] = useState(false);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    const [content, setContent] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [initialLoadDone, setInitialLoadDone] = useState(false);

    const [bibleData, setBibleData] = useState<BibleData | null>(null);
    const [isBibleLoading, setIsBibleLoading] = useState(false);
    const [sceneTexts, setSceneTexts] = useState<string[]>([]);

    const [chapterStatus, setChapterStatus] = useState<'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | undefined>(undefined);

    // Bible search & export
    const [bibleSearchInput, setBibleSearchInput] = useState('');
    const [bibleSearchQuery, setBibleSearchQuery] = useState('');
    const [isExportDropdownOpen, setIsExportDropdownOpen] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const exportDropdownRef = useRef<HTMLDivElement>(null);
    const searchDebounceRef = useRef<ReturnType<typeof setTimeout>>();

    // Chapter export (본문 내보내기)
    const [isChapterExportOpen, setIsChapterExportOpen] = useState(false);
    const [isChapterExporting, setIsChapterExporting] = useState(false);
    const chapterExportRef = useRef<HTMLDivElement>(null);

    // Polling cleanup refs
    const analysisPollingRef = useRef<ReturnType<typeof setTimeout>>();
    const predictionPollingRef = useRef<ReturnType<typeof setTimeout>>();

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

    // Auto-save & unsaved changes
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
    const [charCount, setCharCount] = useState(0);
    const [wordCount, setWordCount] = useState(0);

    // Chapter navigation
    const [chapters, setChapters] = useState<ChapterListItem[]>([]);

    // Refs for auto-save interval (avoid stale closures)
    const hasUnsavedChangesRef = useRef(false);
    const handleSaveRef = useRef<() => Promise<void>>(() => Promise.resolve());

    // Global Theme Sync
    const { theme: globalTheme, setTheme: setGlobalTheme } = useTheme();

    // Reader Mode Settings
    const [readerSettings, setReaderSettings] = useState(() => {
        const saved = localStorage.getItem('reader-settings');
        return saved ? JSON.parse(saved) : {
            fontSize: 18,
            lineHeight: 2.0,
            paragraphSpacing: 40,
            contentWidth: 80,
            fontFamily: 'Noto Serif KR',
            theme: 'light'
        };
    });

    // 1. Sync globalTheme -> readerSettings.theme (when global toggle is clicked)
    useEffect(() => {
        if (mode === 'reader' && readerSettings.theme !== globalTheme) {
            setReaderSettings((prev: any) => ({ ...prev, theme: globalTheme }));
        }
    }, [globalTheme, mode]);

    const handleReaderSettingsChange = (newSettings: any) => {
        setReaderSettings(newSettings);
        // 2. Sync readerSettings.theme -> globalTheme (when reader toolbar setting is changed)
        if (newSettings.theme && newSettings.theme !== globalTheme) {
            setGlobalTheme(newSettings.theme);
        }
    };

    useEffect(() => {
        localStorage.setItem('reader-settings', JSON.stringify(readerSettings));

        // Apply theme to document for reader mode
        if (mode === 'reader') {
            document.documentElement.setAttribute('data-reader-theme', readerSettings.theme);
            document.documentElement.setAttribute('data-theme', readerSettings.theme);
        } else {
            document.documentElement.removeAttribute('data-reader-theme');
            // Restore global theme if needed, but ThemeContext handles that
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

    // Polling for status updates (지수 백오프: 3초 시작, ×1.5, 최대 20초)
    useEffect(() => {
        let timerId: ReturnType<typeof setTimeout>;
        let cancelled = false;

        if (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING') {
            let interval = 3000;
            const poll = async () => {
                if (cancelled || !novelId || !chapterId) return;
                try {
                    const statusData = await getStoryboardStatus(novelId, chapterId);
                    const currentStatus = (statusData.status || '').toUpperCase();

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
                        return; // 완료/실패 시 폴링 중단
                    }
                } catch {
                    toast.error("분석 상태 확인에 실패했습니다.");
                }
                if (!cancelled) {
                    interval = Math.min(interval * 1.5, 20000);
                    timerId = setTimeout(poll, interval);
                }
            };
            poll();
        }

        return () => {
            cancelled = true;
            if (timerId) clearTimeout(timerId);
        };
    }, [chapterStatus, novelId, chapterId]);

    // Cleanup all polling timers on unmount
    useEffect(() => {
        return () => {
            if (analysisPollingRef.current) clearTimeout(analysisPollingRef.current);
            if (predictionPollingRef.current) clearTimeout(predictionPollingRef.current);
        };
    }, []);

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
            setHasUnsavedChanges(false);
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
    const [currentAnalysisType, setCurrentAnalysisType] = useState<string>('consistency');


    const [selectedLocation, setSelectedLocation] = useState<any | null>(null);
    const [extraSectionStates, setExtraSectionStates] = useState<Record<string, boolean>>({});
    const [isAppearancesExpanded, setIsAppearancesExpanded] = useState(false);
    const [isItemAppearancesExpanded, setIsItemAppearancesExpanded] = useState(false);
    const [isLocationAppearancesExpanded, setIsLocationAppearancesExpanded] = useState(false);
    const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
    const scrollHighlightRef = useRef<ReturnType<typeof setTimeout>>();

    // 캐릭터 채팅이 열리면 분석/예측 사이드바 닫기 (겹침 방지)
    useEffect(() => {
        if (showCharacterChat) {
            setIsAnalysisSidebarOpen(false);
            setIsPredictionSidebarOpen(false);
        }
    }, [showCharacterChat]);

    // Keep refs in sync for auto-save interval
    useEffect(() => { hasUnsavedChangesRef.current = hasUnsavedChanges; }, [hasUnsavedChanges]);
    useEffect(() => { handleSaveRef.current = handleSave; });

    // Load chapter list for navigation
    useEffect(() => {
        if (!novelId) return;
        getChapters(novelId).then(chs => {
            setChapters(chs.sort((a, b) => a.chapter_number - b.chapter_number));
        }).catch(() => {});
    }, [novelId]);

    // Auto-save every 30 seconds
    useEffect(() => {
        if (mode === 'reader' || !novelId || !chapterId) return;
        const interval = setInterval(() => {
            if (hasUnsavedChangesRef.current) {
                handleSaveRef.current();
            }
        }, 30000);
        return () => clearInterval(interval);
    }, [novelId, chapterId, mode]);

    // Warn before leaving with unsaved changes
    useEffect(() => {
        const handler = (e: BeforeUnloadEvent) => {
            if (hasUnsavedChangesRef.current) {
                e.preventDefault();
                e.returnValue = '';
            }
        };
        window.addEventListener('beforeunload', handler);
        return () => window.removeEventListener('beforeunload', handler);
    }, []);

    // Keyboard shortcuts
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                if (mode !== 'reader' && novelId && chapterId) {
                    handleSaveRef.current();
                }
            }
            if (e.key === 'Escape') {
                if (isAnalysisSidebarOpen) setIsAnalysisSidebarOpen(false);
                else if (isPredictionSidebarOpen) setIsPredictionSidebarOpen(false);
                else if (isSettingsOpen) setIsSettingsOpen(false);
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [mode, novelId, chapterId, isAnalysisSidebarOpen, isPredictionSidebarOpen, isSettingsOpen]);

    // Calculate char/word count (debounced to avoid re-computing on every keystroke)
    const countTimerRef = useRef<ReturnType<typeof setTimeout>>();
    useEffect(() => {
        if (countTimerRef.current) clearTimeout(countTimerRef.current);
        countTimerRef.current = setTimeout(() => {
            const allText = sceneTexts.length > 0 ? sceneTexts.join('\n\n') : content;
            const plainText = allText.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');
            setCharCount(plainText.replace(/\s/g, '').length);
            const words = plainText.trim().split(/\s+/).filter(Boolean);
            setWordCount(words.length);
        }, 500);
        return () => { if (countTimerRef.current) clearTimeout(countTimerRef.current); };
    }, [content, sceneTexts]);

    // Chapter navigation helpers
    const currentChapterIndex = chapters.findIndex(ch => ch.id === chapterId);
    const prevChapter = currentChapterIndex > 0 ? chapters[currentChapterIndex - 1] : null;
    const nextChapter = currentChapterIndex < chapters.length - 1 ? chapters[currentChapterIndex + 1] : null;

    const navigateToChapter = async (target: ChapterListItem) => {
        if (hasUnsavedChanges && novelId && chapterId) {
            await handleSave();
        }
        onNavigateChapter?.(target.id, target.title);
    };

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
        setIsSettingsOpen(false);

        // Set highlight if provided and not empty
        if (highlightText && highlightText.trim()) {
            setHighlightData({
                sceneIndex: index,
                text: highlightText.trim(),
                timestamp: Date.now()
            });
        }

        // Wait for state updates and then scroll
        if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
        if (scrollHighlightRef.current) clearTimeout(scrollHighlightRef.current);
        scrollTimeoutRef.current = setTimeout(() => {
            const element = document.getElementById(`scene-block-${index}`);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                element.style.transition = 'background-color 0.5s';
                element.style.backgroundColor = 'rgba(79, 70, 229, 0.1)';
                scrollHighlightRef.current = setTimeout(() => {
                    element.style.backgroundColor = 'transparent';
                }, 1000);
            }
        }, 100);
    };

    // 통합 회차 분석 실행 (consistency/plot/style/overall)
    const runChapterAnalysis = async (analysisType: string) => {
        setIsAnalysisLoading(true);
        setAnalysisResult(null);
        setCurrentAnalysisType(analysisType);

        try {
            let task_id: string;

            if (analysisType === 'consistency') {
                const allText = sceneTexts.length > 0
                    ? sceneTexts.join('\n\n')
                    : content;
                const res = await requestConsistencyCheck({
                    novel_id: novelId!,
                    chapter_id: chapterId,
                    text: allText
                });
                task_id = res.task_id;
            } else {
                const res = await requestChapterAnalysis({
                    novel_id: novelId!,
                    chapter_id: chapterId!,
                    analysis_type: analysisType as any
                });
                task_id = res.task_id;
            }

            // 지수 백오프 폴링 (2초 시작, x1.5, 최대 15초, 최대 60회)
            let pollInterval = 2000;
            let pollCount = 0;
            const pollTask = async () => {
                pollCount++;
                if (pollCount > 60) {
                    setIsAnalysisLoading(false);
                    setAnalysisResult({ status: "타임아웃", message: "분석 시간이 너무 오래 걸립니다. 나중에 다시 시도하세요." });
                    return;
                }
                try {
                    const data = await getTaskResult(task_id);

                    if (data.status === "COMPLETED") {
                        setAnalysisResult(data.result as any);
                        setIsAnalysisLoading(false);
                        toast.success("분석이 완료되었습니다.");
                        return;
                    } else if (data.status === "FAILED") {
                        setIsAnalysisLoading(false);
                        setAnalysisResult({ status: "실패", message: data.error || "분석 작업이 실패했습니다." });
                        toast.error("분석 중 오류가 발생했습니다.");
                        return;
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                    setIsAnalysisLoading(false);
                    setAnalysisResult({ status: "오류", message: "상태 확인 중 서버 통신 오류가 발생했습니다." });
                    return;
                }
                pollInterval = Math.min(pollInterval * 1.5, 15000);
                analysisPollingRef.current = setTimeout(pollTask, pollInterval);
            };
            analysisPollingRef.current = setTimeout(pollTask, pollInterval);
        } catch (error) {
            console.error("Analysis error:", error);
            setAnalysisResult({ status: "오류 발생", message: "서버와 통신 중 오류가 발생했습니다." });
            setIsAnalysisLoading(false);
        }
    };

    const handleAnalyze = async (analysisType: string = 'consistency') => {
        setIsAnalysisSidebarOpen(true);
        setIsPredictionSidebarOpen(false);
        setCurrentAnalysisType(analysisType);
        onCloseCharacterChat?.();

        // 캐시 확인
        if (novelId && chapterId) {
            try {
                setIsAnalysisLoading(true);
                const cacheEndpoint = analysisType === 'consistency'
                    ? getCachedConsistency(novelId, chapterId)
                    : getCachedChapterAnalysis(novelId, chapterId, analysisType);
                const cache = await cacheEndpoint;
                if (cache.cached && cache.result) {
                    setAnalysisResult(cache.result);
                    setIsAnalysisLoading(false);
                    return;
                }
            } catch {
                // 캐시 조회 실패 시 무시하고 새 분석 진행
            }
        }

        await runChapterAnalysis(analysisType);
    };

    const handleApplySuggestion = (original: string, suggestion: string) => {
        if (sceneTexts.length > 0) {
            const newSceneTexts = sceneTexts.map(scene => scene.replace(original, suggestion));
            setSceneTexts(newSceneTexts);
            setHasUnsavedChanges(true);
            toast.success("제안이 적용되었습니다.");
        } else {
            const newContent = content.replace(original, suggestion);
            if (newContent !== content) {
                setContent(newContent);
                setHasUnsavedChanges(true);
                toast.success("제안이 적용되었습니다.");
            } else {
                toast.error("해당 문장을 본문에서 찾을 수 없습니다.");
            }
        }
    };

    const handlePredictionSidebarOpen = async () => {
        setIsPredictionSidebarOpen(true);
        setIsAnalysisSidebarOpen(false);
        onCloseCharacterChat?.();

        // DB에서 이전 대화 히스토리 로드 (현재 메시지가 비어 있을 때만)
        if (novelId && chatMessages.length === 0) {
            try {
                const { history } = await getPredictionHistory(novelId);
                if (history.length > 0) {
                    const restored: Message[] = [];
                    for (const item of history) {
                        restored.push({ id: `h-u-${item.id}`, role: 'user', content: item.user_input });
                        restored.push({ id: `h-a-${item.id}`, role: 'assistant', content: item.prediction });
                    }
                    setChatMessages(restored);
                }
            } catch {
                // 히스토리 로드 실패 시 무시
            }
        }
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

            // Poll for result (지수 백오프: 2초 시작, ×1.5, 최대 15초)
            let predPollInterval = 2000;
            const pollPrediction = async () => {
                try {
                    const data = await getPredictionTaskStatus(task_id);

                    if (data.status === "COMPLETED") {
                        // @ts-ignore
                        const resultText = data.result.prediction || data.result.text || (typeof data.result === 'string' ? data.result : JSON.stringify(data.result));

                        const newBotMsg: Message = {
                            id: (Date.now() + 1).toString(),
                            role: 'assistant',
                            content: resultText
                        };

                        setChatMessages(prev => [...prev, newBotMsg]);
                        setIsPredictionLoading(false);

                        if (document.hidden && 'Notification' in window) {
                            if (Notification.permission === "granted") {
                                new Notification("StoryProof 답변 도착", {
                                    body: "챗봇이 응답했습니다.",
                                    icon: "/favicon.ico"
                                });
                            } else if (Notification.permission === "default") {
                                Notification.requestPermission();
                            }
                        }
                        return;
                    } else if (data.status === "FAILED") {
                        setIsPredictionLoading(false);
                        toast.error("답변 생성 중 오류가 발생했습니다.");
                        return;
                    }
                } catch (e) {
                    // Continue polling
                }
                predPollInterval = Math.min(predPollInterval * 1.5, 15000);
                predictionPollingRef.current = setTimeout(pollPrediction, predPollInterval);
            };
            predictionPollingRef.current = setTimeout(pollPrediction, predPollInterval);

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

                foundIndex = sceneTexts.findIndex(s => {
                    const cleanS = superNormalize(s);
                    return cleanS.includes(head) && cleanS.includes(tail);
                });
            }

            if (foundIndex !== -1) {
                scrollToScene(foundIndex, quote);
            } else {
                toast.error('해당 문장을 본문에서 찾을 수 없습니다. (문장이 일부 다르거나 다른 회차의 내용일 수 있습니다)');
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
                        toast.warning('문장을 찾았으나, 정확한 위치 선정이 여려워 이동이 제한됩니다.');
                    }
                } else {
                    toast.error('해당 문장을 본문에서 찾을 수 없습니다.');
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
        setIsSettingsOpen(true);
    };

    // ... (rest of the setup)

    // 바이블 데이터 또는 기본 샘플 데이터
    const characters = useMemo(() => bibleData?.characters && bibleData.characters.length > 0
        ? bibleData.characters
        : [
            { name: '앨리스', first_appearance: 0, appearance_count: 5, appearances: [0, 1, 2, 3, 4], traits: ['호기심 많음', '상상력 풍부'] },
            { name: '흰 토끼', first_appearance: 0, appearance_count: 3, appearances: [0, 1, 3], traits: ['바쁨', '걱정 많음'] },
            { name: '언니', first_appearance: 0, appearance_count: 1, appearances: [0] },
        ], [bibleData]);

    const items = useMemo(() => bibleData?.items && bibleData.items.length > 0
        ? bibleData.items
        : [
            { name: '시계', first_appearance: 0 },
            { name: '책', first_appearance: 0 },
            { name: '데이지 화환', first_appearance: 0 },
        ], [bibleData]);

    const key_events = useMemo(() => bibleData?.key_events && bibleData.key_events.length > 0
        ? bibleData.key_events
        : [
            { summary: '앨리스가 언니 옆 강둑에 앉아 있음', scene_index: 0, importance: '하' },
            { summary: '흰 토끼가 지나가는 것을 목격', scene_index: 1, importance: '중' },
            { summary: '토끼를 따라 토끼 굴로 들어감', scene_index: 2, importance: '상' },
        ], [bibleData]);

    const handleReanalyze = () => {
        if (!novelId || !chapterId) return;

        if (chapterStatus === 'PROCESSING') {
            toast.warning("현재 분석이 진행 중입니다. 잠시만 기다려주세요.");
            return;
        }

        toast("재분석을 진행하시겠습니까?", {
            description: "기존 분석 데이터(인물, 사건 등)가 덮어씌워질 수 있습니다.",
            action: {
                label: "재분석",
                onClick: async () => {
                    setIsAnalyzing(true);
                    setChapterStatus('PROCESSING');
                    try {
                        await reanalyzeChapter(novelId, chapterId);
                        toast.success("재분석 요청이 완료되었습니다. 백그라운드에서 분석이 진행됩니다.");
                    } catch {
                        toast.error("재분석 요청 실패");
                        setChapterStatus('FAILED');
                        setIsAnalyzing(false);
                    }
                }
            },
            cancel: { label: "취소", onClick: () => {} }
        });
    };

    const locations = useMemo(() => bibleData?.locations && bibleData.locations.length > 0
        ? bibleData.locations
        : [
            { name: '강둑', description: '언니와 함께 앉아있던 곳', scenes: [0] },
            { name: '토끼 굴', description: '토끼가 들어간 긴 굴', scenes: [2] },
        ], [bibleData]);

    // Bible search filtering
    const bibleQuery = bibleSearchQuery.trim().toLowerCase();

    const filteredCharacters = useMemo(() => {
        if (!bibleQuery) return characters;
        return characters.filter(c =>
            c.name.toLowerCase().includes(bibleQuery) ||
            ((c as any).description || '').toLowerCase().includes(bibleQuery) ||
            (c.traits || []).some(t => t.toLowerCase().includes(bibleQuery))
        );
    }, [characters, bibleQuery]);

    const filteredItems = useMemo(() => {
        if (!bibleQuery) return items;
        return items.filter(i =>
            i.name.toLowerCase().includes(bibleQuery) ||
            ((i as any).description || '').toLowerCase().includes(bibleQuery)
        );
    }, [items, bibleQuery]);

    const filteredLocations = useMemo(() => {
        if (!bibleQuery) return locations;
        return locations.filter(loc =>
            loc.name.toLowerCase().includes(bibleQuery) ||
            ((loc as any).description || '').toLowerCase().includes(bibleQuery)
        );
    }, [locations, bibleQuery]);

    const filteredKeyEvents = useMemo(() => {
        if (!bibleQuery) return key_events;
        return key_events.filter(e =>
            (e.summary || '').toLowerCase().includes(bibleQuery)
        );
    }, [key_events, bibleQuery]);

    const relationships = useMemo(() => (bibleData?.relationships || []).map((r: any) => ({
        ...r,
        source: r.source || r.character1 || '',
        target: r.target || r.character2 || '',
    })), [bibleData]);

    const filteredRelationships = useMemo(() => {
        if (!bibleQuery) return relationships;
        return relationships.filter((r: any) =>
            (r.source || '').toLowerCase().includes(bibleQuery) ||
            (r.target || '').toLowerCase().includes(bibleQuery) ||
            (r.relation || '').toLowerCase().includes(bibleQuery) ||
            (r.description || '').toLowerCase().includes(bibleQuery)
        );
    }, [relationships, bibleQuery]);

    const matchingScenes = useMemo(() => {
        if (!bibleQuery || !bibleData?.scenes) return [];
        return bibleData.scenes.filter(s =>
            (s.original_text || '').toLowerCase().includes(bibleQuery) ||
            (s.summary || '').toLowerCase().includes(bibleQuery)
        );
    }, [bibleData, bibleQuery]);

    // Debounce search input → bibleSearchQuery (300ms)
    useEffect(() => {
        if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
        searchDebounceRef.current = setTimeout(() => {
            setBibleSearchQuery(bibleSearchInput);
        }, 300);
        return () => { if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current); };
    }, [bibleSearchInput]);

    // Cleanup scroll timeouts on unmount
    useEffect(() => {
        return () => {
            if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current);
            if (scrollHighlightRef.current) clearTimeout(scrollHighlightRef.current);
        };
    }, []);

    // Auto-expand sections when search has matches
    useEffect(() => {
        if (!bibleQuery) return;
        if (filteredCharacters.length > 0) setIsCharactersOpen(true);
        if (filteredItems.length > 0) setIsItemsOpen(true);
        if (filteredLocations.length > 0) setIsLocationsOpen(true);
        if (filteredKeyEvents.length > 0) setIsKeyEventsOpen(true);
    }, [bibleQuery, filteredCharacters.length, filteredItems.length, filteredLocations.length, filteredKeyEvents.length]);

    // Close export dropdown on outside click or Escape
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (exportDropdownRef.current && !exportDropdownRef.current.contains(e.target as Node)) {
                setIsExportDropdownOpen(false);
            }
        };
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isExportDropdownOpen) {
                setIsExportDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        document.addEventListener('keydown', handleKey);
        return () => {
            document.removeEventListener('mousedown', handleClick);
            document.removeEventListener('keydown', handleKey);
        };
    }, [isExportDropdownOpen]);

    // Close chapter export dropdown on outside click or Escape
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (chapterExportRef.current && !chapterExportRef.current.contains(e.target as Node)) {
                setIsChapterExportOpen(false);
            }
        };
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isChapterExportOpen) {
                setIsChapterExportOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClick);
        document.addEventListener('keydown', handleKey);
        return () => {
            document.removeEventListener('mousedown', handleClick);
            document.removeEventListener('keydown', handleKey);
        };
    }, [isChapterExportOpen]);

    const highlightMatch =(text: string, query: string, maxLen: number = 80): JSX.Element => {
        if (!query) return <span>{text.length > maxLen ? text.slice(0, maxLen) + '...' : text}</span>;
        const lowerText = text.toLowerCase();
        const idx = lowerText.indexOf(query.toLowerCase());
        if (idx === -1) return <span>{text.length > maxLen ? text.slice(0, maxLen) + '...' : text}</span>;

        // Extract a window around the match
        const start = Math.max(0, idx - 20);
        const end = Math.min(text.length, idx + query.length + 40);
        const prefix = start > 0 ? '...' : '';
        const suffix = end < text.length ? '...' : '';
        const before = text.slice(start, idx);
        const match = text.slice(idx, idx + query.length);
        const after = text.slice(idx + query.length, end);

        return (
            <span>
                {prefix}{before}<mark className="bible-search-highlight">{match}</mark>{after}{suffix}
            </span>
        );
    };

    const handleExport = async (format: 'txt' | 'pdf' | 'docx') => {
        if (!novelId || !chapterId) return;
        setIsExporting(true);
        setIsExportDropdownOpen(false);
        try {
            await exportBible(novelId, chapterId, format, bibleSearchQuery || undefined);
            toast.success(`${format.toUpperCase()} 파일이 다운로드되었습니다.`);
        } catch (error) {
            toast.error('내보내기에 실패했습니다.');
        } finally {
            setIsExporting(false);
        }
    };

    const handleChapterExport = async (format: 'txt' | 'pdf' | 'docx') => {
        if (!novelId || !chapterId) return;
        setIsChapterExporting(true);
        setIsChapterExportOpen(false);
        try {
            await exportChapter(novelId, chapterId, format);
            toast.success(`${format.toUpperCase()} 파일이 다운로드되었습니다.`);
        } catch (error) {
            toast.error('내보내기에 실패했습니다.');
        } finally {
            setIsChapterExporting(false);
        }
    };

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
                borderBottom: '1px solid var(--border)',
                backgroundColor: 'var(--card)',
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
                    <ArrowLeft size={24} color="var(--muted-foreground)" />
                </button>
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {chapters.length > 1 && prevChapter && (
                        <button
                            onClick={() => navigateToChapter(prevChapter)}
                            title="이전 챕터"
                            style={{
                                padding: '4px',
                                borderRadius: '50%',
                                border: 'none',
                                backgroundColor: 'transparent',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                color: 'var(--muted-foreground)'
                            }}
                        >
                            <ChevronLeft size={20} />
                        </button>
                    )}
                    <h1 className="chapter-detail-title" style={{
                        fontSize: '1.25rem',
                        fontWeight: 600,
                        color: 'var(--foreground)',
                        margin: 0
                    }}>{fileName}</h1>
                    {chapters.length > 1 && nextChapter && (
                        <button
                            onClick={() => navigateToChapter(nextChapter)}
                            title="다음 챕터"
                            style={{
                                padding: '4px',
                                borderRadius: '50%',
                                border: 'none',
                                backgroundColor: 'transparent',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                color: 'var(--muted-foreground)'
                            }}
                        >
                            <ChevronRight size={20} />
                        </button>
                    )}
                </div>
                {novelId && chapterId && mode !== 'reader' && (
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)', whiteSpace: 'nowrap' }}>
                            {charCount.toLocaleString()}자 · {wordCount.toLocaleString()}어절
                        </span>
                        <span style={{
                            fontSize: '0.75rem',
                            color: hasUnsavedChanges ? '#D97706' : 'var(--muted-foreground)',
                            whiteSpace: 'nowrap',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            backgroundColor: hasUnsavedChanges ? 'rgba(217, 119, 6, 0.1)' : 'transparent'
                        }}>
                            {isSaving ? '저장 중...' : hasUnsavedChanges ? '변경사항 있음' : '저장됨'}
                        </span>
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
                                backgroundColor: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? 'var(--muted)' : 'transparent',
                                color: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? 'var(--muted-foreground)' : 'var(--primary)',
                                border: (chapterStatus === 'PROCESSING' || chapterStatus === 'PENDING' || isAnalyzing) ? '1px solid var(--border)' : '1px solid var(--primary)',
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
                                backgroundColor: 'var(--primary)',
                                color: 'var(--primary-foreground)',
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
                        <div className="chapter-export-wrapper" ref={chapterExportRef}>
                            <button
                                className="chapter-export-btn"
                                onClick={() => setIsChapterExportOpen(!isChapterExportOpen)}
                                disabled={isChapterExporting}
                                title="본문 내보내기"
                            >
                                <Download size={16} />
                            </button>
                            {isChapterExportOpen && (
                                <div className="chapter-export-dropdown">
                                    <button onClick={() => handleChapterExport('txt')} className="export-dropdown-item">
                                        <FileText size={14} /> TXT (텍스트)
                                    </button>
                                    <button onClick={() => handleChapterExport('pdf')} className="export-dropdown-item">
                                        <FileIcon size={14} /> PDF
                                    </button>
                                    <button onClick={() => handleChapterExport('docx')} className="export-dropdown-item">
                                        <FileIcon size={14} /> DOCX (워드)
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Author/Reader Toolbar */}
            {
                mode === 'reader' ? (
                    <ReaderToolbar
                        editor={activeEditor}
                        readerSettings={readerSettings}
                        onSettingsChange={handleReaderSettingsChange}
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
                )
            }


            {/* Main Layout */}
            <div className="chapter-detail-layout">
                {/* Sidebar */}
                <div className={`dictionary-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
                    {/* Bible Search & Export Toolbar */}
                    <div className="bible-toolbar">
                        <div className="bible-search-wrapper">
                            <Search size={14} className="bible-search-icon" />
                            <input
                                type="text"
                                className="bible-search-input"
                                placeholder="바이블 검색..."
                                value={bibleSearchInput}
                                maxLength={100}
                                onChange={(e) => setBibleSearchInput(e.target.value)}
                            />
                            {bibleSearchInput && (
                                <button
                                    className="bible-search-clear"
                                    onClick={() => { setBibleSearchInput(''); setBibleSearchQuery(''); }}
                                >
                                    <X size={12} />
                                </button>
                            )}
                        </div>
                        <div className="export-dropdown-wrapper" ref={exportDropdownRef}>
                            <button
                                className="bible-export-btn"
                                onClick={() => setIsExportDropdownOpen(!isExportDropdownOpen)}
                                disabled={isExporting}
                                title={bibleSearchInput ? '검색결과 내보내기' : '바이블 내보내기'}
                            >
                                {isExporting ? (
                                    <Clock size={14} className="spin-animation" />
                                ) : (
                                    <Download size={14} />
                                )}
                            </button>
                            {isExportDropdownOpen && (
                                <div className="export-dropdown">
                                    <button onClick={() => handleExport('txt')} className="export-dropdown-item">
                                        <FileText size={14} />
                                        <span>TXT (텍스트)</span>
                                    </button>
                                    <button onClick={() => handleExport('pdf')} className="export-dropdown-item">
                                        <FileIcon size={14} />
                                        <span>PDF</span>
                                    </button>
                                    <button onClick={() => handleExport('docx')} className="export-dropdown-item">
                                        <FileText size={14} />
                                        <span>DOCX (워드)</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Matching Scenes (search results) */}
                    {bibleQuery && matchingScenes.length > 0 && (
                        <div className="sidebar-section">
                            <div className="section-header active" style={{ cursor: 'default' }}>
                                <div className="section-header-content">
                                    <Search size={18} />
                                    <h3 className="section-title">본문 검색결과 ({matchingScenes.length}건)</h3>
                                </div>
                            </div>
                            <div className="section-content">
                                {matchingScenes.map((scene, idx) => (
                                    <div
                                        key={idx}
                                        className="section-item bible-scene-result interactable"
                                        onClick={() => scrollToScene(scene.scene_index)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <div className="item-name" style={{ fontSize: '0.85rem' }}>
                                            Scene {scene.scene_index + 1}
                                        </div>
                                        <div className="item-description" style={{ fontSize: '0.8rem' }}>
                                            {highlightMatch(scene.original_text, bibleQuery, 100)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {bibleQuery && matchingScenes.length === 0 && filteredCharacters.length === 0 && filteredItems.length === 0 && filteredLocations.length === 0 && filteredKeyEvents.length === 0 && (
                        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--muted-foreground)', fontSize: '0.875rem' }}>
                            검색 결과가 없습니다.
                        </div>
                    )}

                    {/* Characters Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isCharactersOpen ? 'active' : ''}`}
                            onClick={() => setIsCharactersOpen(!isCharactersOpen)}
                        >
                            <div className="section-header-content">
                                <Users size={18} />
                                <h3 className="section-title">인물 {bibleQuery && `(${filteredCharacters.length})`}</h3>
                            </div>
                            {isCharactersOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isCharactersOpen && (
                            <div className="section-content">
                                {isBibleLoading ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>로딩 중...</div>
                                ) : filteredCharacters.length === 0 && bibleQuery ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>매칭 결과 없음</div>
                                ) : (
                                    filteredCharacters.map((character, index) => (
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
                                                                <span key={i} className="trait-tag">
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
                                <h3 className="section-title">아이템 {bibleQuery && `(${filteredItems.length})`}</h3>
                            </div>
                            {isItemsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isItemsOpen && (
                            <div className="section-content">
                                {filteredItems.length === 0 && bibleQuery ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>매칭 결과 없음</div>
                                ) : filteredItems.map((item, index) => (
                                    <div
                                        key={index}
                                        className="section-item interactable"
                                        onClick={() => setSelectedItem(item)}
                                        style={{ cursor: 'pointer', display: 'flex', alignItems: 'flex-start', gap: '8px' }}
                                    >
                                        <span style={{
                                            minWidth: '22px', height: '22px', borderRadius: '50%',
                                            backgroundColor: 'var(--primary, #4F46E5)', color: '#fff',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: '0.7rem', fontWeight: 'bold', flexShrink: 0, marginTop: '2px'
                                        }}>{index + 1}</span>
                                        <div style={{ flex: 1 }}>
                                            <div className="item-name">{item.name}</div>
                                            <div className="item-description">
                                                {typeof (item as any).significance === 'string' && (item as any).significance
                                                    ? (item as any).significance
                                                    : typeof (item as any).description === 'string' && (item as any).description
                                                        ? (item as any).description
                                                        : `첫 등장: ${(item as any).first_appearance + 1}씬`}
                                            </div>
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
                                <h3 className="section-title">장소 {bibleQuery && `(${filteredLocations.length})`}</h3>
                            </div>
                            {isLocationsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isLocationsOpen && (
                            <div className="section-content">
                                {filteredLocations.length === 0 && bibleQuery ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>매칭 결과 없음</div>
                                ) : filteredLocations.map((location, index) => (
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
                    {/* Relationships Section */}
                    {relationships.length > 0 && (
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isRelationshipsOpen ? 'active' : ''}`}
                            onClick={() => setIsRelationshipsOpen(!isRelationshipsOpen)}
                        >
                            <div className="section-header-content">
                                <Link2 size={18} />
                                <h3 className="section-title">인물 관계 {bibleQuery && `(${filteredRelationships.length})`}</h3>
                            </div>
                            {isRelationshipsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isRelationshipsOpen && (
                            <div className="section-content">
                                {filteredRelationships.length === 0 && bibleQuery ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>매칭 결과 없음</div>
                                ) : filteredRelationships.map((rel: any, index: number) => (
                                    <div key={index} className="section-item">
                                        <div className="item-name" style={{ fontSize: '0.9rem' }}>
                                            {rel.source} → {rel.target}
                                        </div>
                                        <div className="item-description">
                                            <span className="trait-tag">{rel.relation || '관계'}</span>
                                            {rel.description && (
                                                <span style={{ marginLeft: '6px' }}>{rel.description.length > 40 ? rel.description.slice(0, 40) + '...' : rel.description}</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                    )}

                    {/* Key Events Section */}
                    <div className="sidebar-section">
                        <button
                            className={`section-header ${isKeyEventsOpen ? 'active' : ''}`}
                            onClick={() => setIsKeyEventsOpen(!isKeyEventsOpen)}
                        >
                            <div className="section-header-content">
                                <Clock size={18} />
                                <h3 className="section-title">주요 사건 {bibleQuery && `(${filteredKeyEvents.length})`}</h3>
                            </div>
                            {isKeyEventsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isKeyEventsOpen && (
                            <div className="section-content">
                                {filteredKeyEvents.length === 0 && bibleQuery ? (
                                    <div style={{ padding: '10px', fontSize: '12px', color: '#999' }}>매칭 결과 없음</div>
                                ) : filteredKeyEvents.map((event, index) => (
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
                    {bibleData && Object.keys(bibleData).filter(key => !['characters', 'items', 'timeline', 'locations', 'key_events', 'scenes', 'relationships', 'chapter_id'].includes(key)).map(key => {
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
                                    backgroundColor: mode === 'reader' ? 'var(--reader-bg)' : 'var(--background)'
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
                                            color: 'var(--primary)',
                                            backgroundColor: 'var(--card)',
                                            padding: '2px 10px',
                                            borderRadius: '12px',
                                            border: '1px solid var(--border)',
                                            zIndex: 5,
                                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
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
                                                    setHasUnsavedChanges(true);
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
                                    onUpdate={(html) => { setContent(html); setHasUnsavedChanges(true); }}
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
                                backgroundColor: 'var(--modal-bg, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--modal-text, #333)',
                                border: '1px solid var(--modal-border, #e5e7eb)'
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
                                        backgroundColor: 'var(--muted, #f1f5f9)',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: 'var(--muted-foreground, #94a3b8)',
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
                                        backgroundColor: isImageGenerating ? 'var(--muted, #cbd5e1)' : 'var(--primary, #4f46e5)',
                                        color: 'var(--primary-foreground, white)',
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
                                    <div style={{ fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginBottom: '4px' }}>별칭</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        {selectedCharacter.aliases.map((alias: string, i: number) => (
                                            <span key={i} style={{
                                                fontSize: '0.8rem',
                                                padding: '2px 8px',
                                                backgroundColor: 'var(--muted, #f1f5f9)',
                                                borderRadius: '12px',
                                                color: 'var(--muted-foreground, #475569)',
                                                border: '1px solid var(--border)',
                                                opacity: 0.9
                                            }}>
                                                {alias}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div style={{ marginBottom: '16px' }}>
                                <div style={{ fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginBottom: '4px' }}>설명</div>
                                <p style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0 }}>
                                    {selectedCharacter.description || "상세 설명이 없습니다."}
                                </p>
                            </div>

                            {selectedCharacter.traits && selectedCharacter.traits.length > 0 && (
                                <div style={{ marginBottom: '16px' }}>
                                    <div style={{ fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginBottom: '4px' }}>특징</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                        {selectedCharacter.traits.map((trait: string, i: number) => (
                                            <span key={i} style={{
                                                fontSize: '0.8rem',
                                                padding: '4px 10px',
                                                backgroundColor: 'var(--muted, rgba(79, 70, 229, 0.1))',
                                                color: 'var(--primary, #4F46E5)',
                                                borderRadius: '6px',
                                                fontWeight: '500',
                                                border: '1px solid var(--border)'
                                            }}>
                                                {trait}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginTop: '24px', borderTop: '1px solid var(--border, #eee)', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <strong style={{ color: 'var(--modal-text)' }}>첫 등장:</strong>
                                    <button
                                        onClick={() => scrollToScene(selectedCharacter.first_appearance, selectedCharacter.name)}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            color: 'var(--primary, #4F46E5)',
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
                                        <strong style={{ color: 'var(--modal-text)' }}>총 등장:</strong> {selectedCharacter.appearance_count}회
                                        {(selectedCharacter.appearances && selectedCharacter.appearances.length > 0) && (
                                            <button
                                                onClick={() => setIsAppearancesExpanded(!isAppearancesExpanded)}
                                                style={{
                                                    background: 'var(--modal-bg)',
                                                    border: '1px solid var(--border, #e2e8f0)',
                                                    borderRadius: '4px',
                                                    cursor: 'pointer',
                                                    padding: '2px 6px',
                                                    fontSize: '0.8rem',
                                                    color: 'var(--muted-foreground, #666)',
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
                                                        background: 'var(--muted, #f1f5f9)',
                                                        border: '1px solid var(--border)',
                                                        borderRadius: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        color: 'var(--muted-foreground, #475569)',
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
                                backgroundColor: 'var(--modal-bg, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--modal-text, #333)',
                                border: '1px solid var(--modal-border, #e5e7eb)'
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
                                        backgroundColor: 'var(--muted, #f1f5f9)',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: 'var(--muted-foreground, #94a3b8)',
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
                                        backgroundColor: isImageGenerating ? 'var(--muted, #cbd5e1)' : 'var(--primary, #4f46e5)',
                                        color: 'var(--primary-foreground, white)',
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
                                <div style={{ fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginBottom: '4px' }}>설명</div>
                                <p style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0 }}>
                                    {selectedItem.description || "상세 설명이 없습니다."}
                                </p>
                            </div>

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginTop: '24px', borderTop: '1px solid var(--border, #eee)', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <strong style={{ color: 'var(--modal-text)' }}>첫 등장:</strong>
                                        <button
                                            onClick={() => scrollToScene(selectedItem.first_appearance, selectedItem.name)}
                                            style={{
                                                background: 'none',
                                                border: 'none',
                                                color: 'var(--primary, #4F46E5)',
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
                                            <strong style={{ color: 'var(--modal-text)' }}>총 등장:</strong> {selectedItem.appearance_count}회
                                            {(selectedItem.appearances && selectedItem.appearances.length > 0) && (
                                                <button
                                                    onClick={() => setIsItemAppearancesExpanded(!isItemAppearancesExpanded)}
                                                    style={{
                                                        background: 'var(--modal-bg)',
                                                        border: '1px solid var(--border, #e2e8f0)',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        padding: '2px 6px',
                                                        fontSize: '0.8rem',
                                                        color: 'var(--muted-foreground, #666)',
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
                                                        background: 'var(--muted, #f1f5f9)',
                                                        border: '1px solid var(--border)',
                                                        borderRadius: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        color: 'var(--muted-foreground, #475569)',
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
                                backgroundColor: 'var(--modal-bg, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--modal-text, #333)',
                                border: '1px solid var(--modal-border, #e5e7eb)'
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
                                        backgroundColor: 'var(--muted, #f1f5f9)',
                                        borderRadius: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: 'var(--muted-foreground, #94a3b8)',
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
                                        backgroundColor: isImageGenerating ? 'var(--muted, #cbd5e1)' : 'var(--primary, #4f46e5)',
                                        color: 'var(--primary-foreground, white)',
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
                                <div style={{ fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginBottom: '4px' }}>설명</div>
                                <p style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0 }}>
                                    {selectedLocation.description || "상세 설명이 없습니다."}
                                </p>
                            </div>

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginTop: '24px', borderTop: '1px solid var(--border, #eee)', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <strong style={{ color: 'var(--modal-text)' }}>총 등장:</strong> {selectedLocation.appearance_count || (selectedLocation.scenes ? selectedLocation.scenes.length : 0)}회
                                        {(selectedLocation.scenes && selectedLocation.scenes.length > 0) && (
                                            <button
                                                onClick={() => setIsLocationAppearancesExpanded(!isLocationAppearancesExpanded)}
                                                style={{
                                                    background: 'var(--modal-bg)',
                                                    border: '1px solid var(--border, #e2e8f0)',
                                                    borderRadius: '4px',
                                                    cursor: 'pointer',
                                                    padding: '2px 6px',
                                                    fontSize: '0.8rem',
                                                    color: 'var(--muted-foreground, #666)',
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
                                                        background: 'var(--secondary)',
                                                        border: '1px solid var(--border)',
                                                        borderRadius: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        color: 'var(--primary)',
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
                                backgroundColor: 'var(--modal-bg, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--modal-text, #333)',
                                border: '1px solid var(--modal-border, #e5e7eb)'
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
                                        backgroundColor: 'var(--muted, #f1f5f9)',
                                        borderRadius: '4px',
                                        fontSize: '0.875rem',
                                        fontWeight: '500',
                                        color: 'var(--muted-foreground, #475569)',
                                        marginTop: '8px'
                                    }}>
                                        중요도: {selectedKeyEvent.importance}
                                    </div>
                                )}
                            </div>

                            <div style={{ display: 'flex', gap: '16px', fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginTop: '16px', borderTop: '1px solid var(--border, #eee)', paddingTop: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', width: '100%' }}>
                                    <button
                                        onClick={() => scrollToScene(selectedKeyEvent.scene_index)}
                                        style={{
                                            width: '100%',
                                            background: 'var(--primary, #4F46E5)',
                                            border: 'none',
                                            borderRadius: '6px',
                                            padding: '10px 16px',
                                            fontSize: '0.95rem',
                                            fontWeight: '600',
                                            color: 'var(--primary-foreground, #ffffff)',
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
                                backgroundColor: 'var(--modal-bg, #fff)',
                                padding: '24px',
                                borderRadius: '12px',
                                width: '400px',
                                maxWidth: '90%',
                                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                                color: 'var(--modal-text, #333)',
                                border: '1px solid var(--modal-border, #e5e7eb)'
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
                                <div style={{ fontSize: '0.875rem', color: 'var(--muted-foreground, #666)', marginBottom: '4px' }}>{selectedExtraItem.title.toUpperCase()}</div>
                                <div style={{ lineHeight: '1.6', fontSize: '1rem', margin: 0, maxHeight: '300px', overflowY: 'auto' }}>
                                    {selectedExtraItem.item.description || selectedExtraItem.item.summary || (
                                        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem', backgroundColor: 'var(--muted, #f1f5f9)', color: 'var(--modal-text)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
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

            {/* Settings Modal - Floating Panel Style */}
            {isSettingsOpen && (
                <div style={{
                    position: 'fixed',
                    bottom: '20px',
                    right: '25px',
                    width: '600px',
                    height: '750px',
                    zIndex: 1002,
                    animation: 'slideUp 0.3s ease'
                }}>
                    <Settings onClose={() => setIsSettingsOpen(false)} />
                </div>
            )}

            {/* 설정 파괴 분석 결과 사이드바 */}
            <AnalysisSidebar
                isOpen={isAnalysisSidebarOpen}
                onClose={() => setIsAnalysisSidebarOpen(false)}
                result={analysisResult}
                isLoading={isAnalysisLoading}
                onNavigateToQuote={handleNavigateToQuote}
                onReanalyze={() => runChapterAnalysis(currentAnalysisType)}
                onApplySuggestion={handleApplySuggestion}
                analysisType={currentAnalysisType}
            />

            {/* 스토리 예측 사이드바 */}
            <PredictionSidebar
                isOpen={isPredictionSidebarOpen}
                onClose={() => setIsPredictionSidebarOpen(false)}
                messages={chatMessages}
                onSendMessage={handleSendMessage}
                isLoading={isPredictionLoading}
                onClearChat={() => {
                    setChatMessages([]);
                    if (novelId) clearPredictionHistory(novelId).catch(() => {});
                }}
            />

            {/* Floating Menu - Settings, Analysis, Prediction, Chatbot */}
            <FloatingMenu
                onNavigateToScene={scrollToScene}
                onAnalyze={handleAnalyze}
                onPredictStory={handlePredictStoryTrigger}
                onOpenCharacterChat={onOpenCharacterChat}
                onOpenSettings={handleOpenSettings}
                onOpenRelGraph={() => setIsRelGraphOpen(true)}
                novelId={novelId}
                chapterId={chapterId}
                mode={mode}
            />

            {/* 인물 관계도 모달 */}
            <RelationshipGraphModal
                isOpen={isRelGraphOpen}
                onClose={() => setIsRelGraphOpen(false)}
                relationships={relationships.map((r: any) => ({
                    source: r.source || r.character1,
                    target: r.target || r.character2,
                    relation: r.relation, description: r.description
                }))}
                characters={bibleData?.characters?.map((c: any) => ({
                    name: c.name,
                    description: c.description,
                    traits: c.traits,
                    appearance_count: c.appearance_count
                })) || []}
            />
        </div >
    );
}
