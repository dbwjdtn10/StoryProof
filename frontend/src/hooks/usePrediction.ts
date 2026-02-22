import { useState, useRef, useEffect } from 'react';
import { toast } from 'sonner';
import { requestPrediction, getPredictionTaskStatus, getPredictionHistory } from '../api/prediction';
import { Message } from '../components/predictions/PredictionSidebar';

interface UsePredictionCallbacks {
    onOpen?: () => void;
}

export function usePrediction(
    novelId?: number,
    callbacks?: UsePredictionCallbacks
): {
    isPredictionSidebarOpen: boolean;
    setIsPredictionSidebarOpen: (open: boolean) => void;
    chatMessages: Message[];
    setChatMessages: React.Dispatch<React.SetStateAction<Message[]>>;
    isPredictionLoading: boolean;
    handlePredictionSidebarOpen: () => Promise<void>;
    handleSendMessage: (inputMessage: string) => Promise<void>;
} {
    const [isPredictionSidebarOpen, setIsPredictionSidebarOpen] = useState(false);
    const [chatMessages, setChatMessages] = useState<Message[]>([]);
    const [isPredictionLoading, setIsPredictionLoading] = useState(false);

    const predictionPollingRef = useRef<ReturnType<typeof setTimeout>>();

    // Cleanup polling timer on unmount
    useEffect(() => {
        return () => {
            if (predictionPollingRef.current) clearTimeout(predictionPollingRef.current);
        };
    }, []);

    const handlePredictionSidebarOpen = async () => {
        setIsPredictionSidebarOpen(true);
        callbacks?.onOpen?.();

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

            // Poll for result (지수 백오프: 2초 시작, x1.5, 최대 15초)
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

    return {
        isPredictionSidebarOpen,
        setIsPredictionSidebarOpen,
        chatMessages,
        setChatMessages,
        isPredictionLoading,
        handlePredictionSidebarOpen,
        handleSendMessage,
    };
}
