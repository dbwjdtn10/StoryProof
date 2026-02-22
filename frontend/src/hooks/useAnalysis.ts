import { useState, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { getCachedConsistency, requestConsistencyCheck, getTaskResult, requestChapterAnalysis, getCachedChapterAnalysis } from '../api/analysis';
import { AnalysisResult } from '../components/AnalysisSidebar';

interface UseAnalysisCallbacks {
    onOpen?: () => void;
}

export function useAnalysis(
    novelId?: number,
    chapterId?: number,
    getTextContent?: () => string,
    callbacks?: UseAnalysisCallbacks
): {
    isAnalysisSidebarOpen: boolean;
    setIsAnalysisSidebarOpen: (open: boolean) => void;
    isAnalysisLoading: boolean;
    analysisResult: AnalysisResult | null;
    isCachedResult: boolean;
    currentAnalysisType: string;
    handleAnalyze: (analysisType?: string) => Promise<void>;
    reanalyze: () => Promise<void>;
} {
    const [isAnalysisSidebarOpen, setIsAnalysisSidebarOpen] = useState(false);
    const [isAnalysisLoading, setIsAnalysisLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
    const [isCachedResult, setIsCachedResult] = useState(false);
    const [currentAnalysisType, setCurrentAnalysisType] = useState<string>('consistency');

    const analysisPollingRef = useRef<ReturnType<typeof setTimeout>>();

    // Cleanup polling timer on unmount
    useEffect(() => {
        return () => {
            if (analysisPollingRef.current) clearTimeout(analysisPollingRef.current);
        };
    }, []);

    // 통합 회차 분석 실행 (consistency/plot/style/overall)
    const runChapterAnalysis = async (analysisType: string) => {
        setIsAnalysisLoading(true);
        setAnalysisResult(null);
        setIsCachedResult(false);
        setCurrentAnalysisType(analysisType);

        try {
            let task_id: string;

            if (analysisType === 'consistency') {
                const allText = getTextContent ? getTextContent() : '';
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
                    setAnalysisResult({ status: "\ud0c0\uc784\uc544\uc6c3", message: "\ubd84\uc11d \uc2dc\uac04\uc774 \ub108\ubb34 \uc624\ub798 \uac78\ub9bd\ub2c8\ub2e4. \ub098\uc911\uc5d0 \ub2e4\uc2dc \uc2dc\ub3c4\ud558\uc138\uc694." });
                    return;
                }
                try {
                    const data = await getTaskResult(task_id);

                    if (data.status === "COMPLETED") {
                        setAnalysisResult(data.result as any);
                        setIsAnalysisLoading(false);
                        toast.success("\ubd84\uc11d\uc774 \uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4.");
                        return;
                    } else if (data.status === "FAILED") {
                        setIsAnalysisLoading(false);
                        setAnalysisResult({ status: "\uc2e4\ud328", message: data.error || "\ubd84\uc11d \uc791\uc5c5\uc774 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4." });
                        toast.error("\ubd84\uc11d \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4.");
                        return;
                    }
                } catch (err) {
                    console.error("Polling error:", err);
                    setIsAnalysisLoading(false);
                    setAnalysisResult({ status: "\uc624\ub958", message: "\uc0c1\ud0dc \ud655\uc778 \uc911 \uc11c\ubc84 \ud1b5\uc2e0 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4." });
                    return;
                }
                pollInterval = Math.min(pollInterval * 1.5, 15000);
                analysisPollingRef.current = setTimeout(pollTask, pollInterval);
            };
            analysisPollingRef.current = setTimeout(pollTask, pollInterval);
        } catch (error) {
            console.error("Analysis error:", error);
            setAnalysisResult({ status: "\uc624\ub958 \ubc1c\uc0dd", message: "\uc11c\ubc84\uc640 \ud1b5\uc2e0 \uc911 \uc624\ub958\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4." });
            setIsAnalysisLoading(false);
        }
    };

    const handleAnalyze = async (analysisType: string = 'consistency') => {
        setIsAnalysisSidebarOpen(true);
        setCurrentAnalysisType(analysisType);
        callbacks?.onOpen?.();

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
                    setIsCachedResult(true);
                    setIsAnalysisLoading(false);
                    return;
                }
            } catch {
                // 캐시 조회 실패 시 무시하고 새 분석 진행
            }
        }

        await runChapterAnalysis(analysisType);
    };

    const reanalyze = async () => {
        await runChapterAnalysis(currentAnalysisType);
    };

    return {
        isAnalysisSidebarOpen,
        setIsAnalysisSidebarOpen,
        isAnalysisLoading,
        analysisResult,
        isCachedResult,
        currentAnalysisType,
        handleAnalyze,
        reanalyze,
    };
}
