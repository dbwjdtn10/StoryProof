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

    const executeMerge = async () => {
        if (!novelId || selectedSourceIds.length < 2) {
            toast.warning("합칠 파일을 2개 이상 선택해 주세요.");
            return;
        }

        setIsMerging(true);

        try {
            // First selected ID is the target by default interaction logic,
            // but effectively the backend will sort them and use target_id as the container.
            // Let's use the first selected item as the target container for simplicity of ID tracking.
            const targetId = selectedSourceIds[0];
            const sourceIds = selectedSourceIds.slice(1);

            // Note: The backend logic I implemented treats 'source_ids' + 'target_id' as the set.
            // So I should pass the others as source_ids.

            const result = await mergeChapters(novelId, targetId, sourceIds);

            toast.success("파일이 성공적으로 병합되었습니다.");

            setIsMergeMode(false);
            setSelectedSourceIds([]);

            if (onSuccess) {
                onSuccess(result.id);
            }

        } catch (error) {
            console.error("Merge failed:", error);
            toast.error("파일 병합에 실패했습니다.");
        } finally {
            setIsMerging(false);
        }
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
