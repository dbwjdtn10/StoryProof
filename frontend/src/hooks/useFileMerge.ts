import { useState } from 'react';
import { toast } from 'sonner';
import { mergeChapters } from '../api/novel';

interface UseFileMergeProps {
    novelId?: number;
    onSuccess: (newId: number) => void;
}

export function useFileMerge({ novelId, onSuccess }: UseFileMergeProps) {
    const [isMergeMode, setIsMergeMode] = useState(false);
    const [selectedSourceIds, setSelectedSourceIds] = useState<number[]>([]);
    const [isMerging, setIsMerging] = useState(false);

    const toggleMergeMode = () => {
        setIsMergeMode(prev => !prev);
        if (isMergeMode) {
            setSelectedSourceIds([]);
        }
    };

    const handleFileSelect = (fileId: number) => {
        if (!isMergeMode) return;
        setSelectedSourceIds(prev =>
            prev.includes(fileId) ? prev.filter(id => id !== fileId) : [...prev, fileId]
        );
    };

    const cancelMerge = () => {
        setIsMergeMode(false);
        setSelectedSourceIds([]);
    };

    const executeMerge = () => {
        if (!novelId || selectedSourceIds.length < 2) {
            toast.error("합칠 파일을 2개 이상 선택해 주세요.");
            return;
        }

        toast(`${selectedSourceIds.length}개의 파일을 병합하시겠습니까?`, {
            description: "병합 후 원본 파일들은 삭제됩니다.",
            action: {
                label: "병합",
                onClick: async () => {
                    setIsMerging(true);
                    try {
                        const targetId = selectedSourceIds[0];
                        const sourceIds = selectedSourceIds.slice(1);
                        const result = await mergeChapters(novelId, targetId, sourceIds);
                        toast.success("파일이 성공적으로 병합되었습니다.");
                        setIsMergeMode(false);
                        setSelectedSourceIds([]);
                        if (onSuccess) onSuccess(result.id);
                    } catch (error) {
                        console.error("Merge failed:", error);
                        toast.error("파일 병합에 실패했습니다.");
                    } finally {
                        setIsMerging(false);
                    }
                }
            },
            cancel: { label: "취소", onClick: () => {} }
        });
    };

    return {
        isMergeMode,
        selectedSourceIds,
        isMerging,
        toggleMergeMode,
        handleFileSelect,
        executeMerge,
        cancelMerge,
        setIsMergeMode,
        setSelectedSourceIds
    };
}
