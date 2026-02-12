import { useState } from 'react';
import { toast } from 'sonner';
import { requestImageGeneration, getImageTaskStatus, refinePromptWithGemini } from '../api/image';

export function useImageGeneration() {
    const [isGenerating, setIsGenerating] = useState(false);
    const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(null);

    const generateImage = async (prompt: string) => { // prompt는 사용자가 입력한 한국어 원본
        if (!prompt) return;
        
        setIsGenerating(true);
        setGeneratedImageUrl(null); 
        
        try {
            // [중요] 1. Gemini 정제 결과를 변수에 확실히 담습니다.
            console.log("정제 요청 중 (원본):", prompt);
            const refinedPrompt = await refinePromptWithGemini(prompt);
            
            // 2. 만약 정제 결과가 없거나 실패했다면 원본을 쓰도록 방어 로직 추가
            const finalPrompt = refinedPrompt || prompt;
            console.log("정제 완료 (전송될 값):", finalPrompt);
        
            // [중요] 3. 여기서 반드시 finalPrompt(정제된 영어)를 넘겨야 합니다!
            const { task_id } = await requestImageGeneration(finalPrompt);
            
            // 3. 폴링(Polling) 시작: 일정 간격으로 작업 완료 여부 확인
            const pollInterval = setInterval(async () => {
                try {
                    const statusData = await getImageTaskStatus(task_id);
                    
                    if (statusData.status === 'SUCCESS' && statusData.image_url) {
                        setGeneratedImageUrl(statusData.image_url);
                        setIsGenerating(false);
                        clearInterval(pollInterval);
                        toast.success("장면 시각화가 완료되었습니다.");
                    } else if (statusData.status === 'FAILURE') {
                        setIsGenerating(false);
                        clearInterval(pollInterval);
                        // Safety Filter에 의해 실패했을 가능성을 안내
                        toast.error("이미지 생성에 실패했습니다. (부적절한 묘사가 포함되었을 수 있습니다.)");
                    }
                } catch (err) {
                    clearInterval(pollInterval);
                    setIsGenerating(false);
                }
            }, 3000); 
            
        } catch (error) {
            console.error("Image Generation Error:", error);
            toast.error("이미지 생성 요청 중 오류가 발생했습니다.");
            setIsGenerating(false);
        }
    };

    return { generateImage, isGenerating, generatedImageUrl, setGeneratedImageUrl };
}