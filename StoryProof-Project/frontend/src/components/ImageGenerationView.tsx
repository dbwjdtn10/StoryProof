import { useImageGeneration } from '../hooks/useImageGeneration';
import { Loader2, Image as ImageIcon, Sparkles } from 'lucide-react';

interface ImageGenerationViewProps {
    prompt: string;
    label: string;
}

export function ImageGenerationView({ prompt, label }: ImageGenerationViewProps) {
    const { 
        generateImage, 
        isGenerating, 
        generatedImageUrl 
    } = useImageGeneration();

    return (
        <div style={{ 
            marginBottom: '20px', 
            padding: '16px', 
            backgroundColor: '#F8FAFC', 
            borderRadius: '8px', 
            border: '1px solid #E2E8F0' 
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <Sparkles size={18} color="#4F46E5" />
                <span style={{ fontSize: '0.9rem', fontWeight: '600', color: '#475569' }}>AI {label} 시각화</span>
            </div>
                        
            {/* 결과 이미지 표시 */}
            {generatedImageUrl && (
                <div style={{ marginBottom: '16px', borderRadius: '6px', overflow: 'hidden', border: '1px solid #e2e8f0' }}>
                    <img src={generatedImageUrl} alt={label} style={{ width: '100%', height: 'auto', display: 'block' }} />
                </div>
            )}
            
            <button
                onClick={() => generateImage(prompt)}
                disabled={isGenerating} // isGenerating 사용
                style={{
                    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    gap: '8px', padding: '10px', backgroundColor: isGenerating ? '#94A3B8' : '#4F46E5', 
                    color: 'white', border: 'none', borderRadius: '6px', 
                    cursor: isGenerating ? 'not-allowed' : 'pointer', fontWeight: '600'
                }}
            >
                {isGenerating ? <Loader2 className="animate-spin" size={18} /> : <ImageIcon size={18} />}
                {isGenerating ? `${label} 그리는 중...` : generatedImageUrl ? '다시 생성하기' : `이 ${label}를 이미지로 생성`}
            </button>
        </div>
    );
}