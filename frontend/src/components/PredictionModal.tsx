import { X, Sparkles, Loader2 } from 'lucide-react';
import { useState } from 'react';

interface PredictionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onPredict: (scenario: string) => Promise<string | null>;
}

export function PredictionModal({ isOpen, onClose, onPredict }: PredictionModalProps) {
    const [scenario, setScenario] = useState('');
    const [prediction, setPrediction] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    if (!isOpen) return null;

    const handlePredict = async () => {
        if (!scenario.trim()) {
            alert('시나리오를 입력해주세요.');
            return;
        }

        setIsLoading(true);
        setPrediction(null);

        try {
            const result = await onPredict(scenario);
            setPrediction(result);
        } catch (error) {
            alert('예측 중 오류가 발생했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleClose = () => {
        setScenario('');
        setPrediction(null);
        setIsLoading(false);
        onClose();
    };

    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 2000
            }}
            onClick={handleClose}
        >
            <div
                style={{
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    width: '90%',
                    maxWidth: '700px',
                    maxHeight: '85vh',
                    display: 'flex',
                    flexDirection: 'column',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)'
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div
                    style={{
                        padding: '20px 24px',
                        borderBottom: '1px solid #e5e7eb',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        backgroundColor: '#f9fafb'
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <Sparkles size={24} color="#7C3AED" />
                        <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
                            스토리 예측 (What-If)
                        </h2>
                    </div>
                    <button
                        onClick={handleClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            padding: '4px',
                            color: '#6b7280'
                        }}
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
                    {/* Input Section */}
                    <div style={{ marginBottom: '24px' }}>
                        <label
                            htmlFor="scenario-input"
                            style={{
                                display: 'block',
                                marginBottom: '8px',
                                fontSize: '0.95rem',
                                fontWeight: '600',
                                color: '#374151'
                            }}
                        >
                            가정 시나리오를 입력하세요:
                        </label>
                        <textarea
                            id="scenario-input"
                            value={scenario}
                            onChange={(e) => setScenario(e.target.value)}
                            placeholder="예: 만약 주인공이 그 선택을 하지 않았다면?"
                            style={{
                                width: '100%',
                                minHeight: '120px',
                                padding: '12px',
                                fontSize: '0.95rem',
                                border: '1px solid #d1d5db',
                                borderRadius: '8px',
                                resize: 'vertical',
                                fontFamily: 'inherit',
                                lineHeight: '1.5'
                            }}
                        />
                    </div>

                    {/* Predict Button */}
                    <button
                        onClick={handlePredict}
                        disabled={isLoading || !scenario.trim()}
                        style={{
                            width: '100%',
                            padding: '12px',
                            backgroundColor: isLoading || !scenario.trim() ? '#9ca3af' : '#7C3AED',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            fontSize: '1rem',
                            fontWeight: '600',
                            cursor: isLoading || !scenario.trim() ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            marginBottom: '24px'
                        }}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                                예측 중...
                            </>
                        ) : (
                            <>
                                <Sparkles size={20} />
                                스토리 예측하기
                            </>
                        )}
                    </button>

                    {/* Prediction Result */}
                    {prediction && (
                        <div
                            style={{
                                padding: '20px',
                                backgroundColor: '#F5F3FF',
                                border: '1px solid #DDD6FE',
                                borderRadius: '8px'
                            }}
                        >
                            <h3
                                style={{
                                    margin: '0 0 12px 0',
                                    fontSize: '1rem',
                                    fontWeight: '600',
                                    color: '#7C3AED',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}
                            >
                                <Sparkles size={18} />
                                예측 결과:
                            </h3>
                            <div
                                style={{
                                    fontSize: '0.95rem',
                                    lineHeight: '1.7',
                                    color: '#374151',
                                    whiteSpace: 'pre-wrap'
                                }}
                            >
                                {prediction}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Add CSS for spinner animation */}
            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}
