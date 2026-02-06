import React from 'react';
import { ShieldAlert, CheckCircle, X, AlertTriangle, Lightbulb, MapPin } from 'lucide-react';

interface AnalysisError {
    category: string;
    violation_point: string;
    reason: string;
    suggestion: string;
    scene_index?: number;
}

interface AnalysisResult {
    status: string;
    errors?: AnalysisError[];
    message?: string;
}

interface AnalysisResultModalProps {
    isOpen: boolean;
    onClose: () => void;
    onNavigate?: (sceneIndex: number) => void;
    result: AnalysisResult | null;
    isLoading: boolean;
}

export function AnalysisResultModal({ isOpen, onClose, onNavigate, result, isLoading }: AnalysisResultModalProps) {
    if (!isOpen) return null;

    const getCategoryStyles = (category: string) => {
        if (category.includes('설정 충돌')) return { bg: '#FEF2F2', border: '#FECACA', text: '#991B1B', icon: <ShieldAlert size={18} /> };
        if (category.includes('개연성')) return { bg: '#FFFBEB', border: '#FDE68A', text: '#92400E', icon: <AlertTriangle size={18} /> };
        if (category.includes('보이스')) return { bg: '#F5F3FF', border: '#DDD6FE', text: '#5B21B6', icon: <Lightbulb size={18} /> };
        return { bg: '#F9FAFB', border: '#E5E7EB', text: '#374151', icon: <AlertTriangle size={18} /> };
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
            backdropFilter: 'blur(4px)'
        }} onClick={onClose}>
            <div style={{
                backgroundColor: 'white',
                borderRadius: '16px',
                width: '600px',
                maxWidth: '95%',
                padding: '32px',
                boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
                position: 'relative',
                animation: 'slideUp 0.3s ease-out',
                maxHeight: '90vh',
                display: 'flex',
                flexDirection: 'column'
            }} onClick={e => e.stopPropagation()}>

                <button
                    onClick={onClose}
                    style={{
                        position: 'absolute',
                        top: '16px',
                        right: '16px',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: '#9ca3af',
                        zIndex: 10
                    }}
                >
                    <X size={24} />
                </button>

                {isLoading ? (
                    <div style={{ textAlign: 'center', padding: '40px 0' }}>
                        <div className="spinner" style={{
                            width: '40px',
                            height: '40px',
                            border: '4px solid #e5e7eb',
                            borderTop: '4px solid #4F46E5',
                            borderRadius: '50%',
                            margin: '0 auto 16px',
                            animation: 'spin 1s linear infinite'
                        }}></div>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#1f2937', marginBottom: '8px' }}>
                            설정 파괴 분석 중...
                        </h3>
                        <p style={{ color: '#6b7280' }}>
                            AI가 소설의 설정 오류를 정밀하게 검사하고 있습니다.<br />
                            잠시만 기다려주세요.
                        </p>
                    </div>
                ) : result ? (
                    <div style={{ overflowY: 'auto', paddingRight: '8px' }}>
                        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                            {result.status === "설정 파괴 감지" ? (
                                <div style={{
                                    width: '64px',
                                    height: '64px',
                                    backgroundColor: '#FEE2E2',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    margin: '0 auto 16px',
                                    color: '#EF4444'
                                }}>
                                    <ShieldAlert size={32} />
                                </div>
                            ) : (
                                <div style={{
                                    width: '64px',
                                    height: '64px',
                                    backgroundColor: '#D1FAE5',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    margin: '0 auto 16px',
                                    color: '#059669'
                                }}>
                                    <CheckCircle size={32} />
                                </div>
                            )}

                            <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937', margin: 0 }}>
                                {result.status === "설정 파괴 감지" ? "설정 오류가 감지되었습니다" : "설정이 완벽합니다!"}
                            </h2>
                        </div>

                        {result.status === "설정 파괴 감지" && result.errors && result.errors.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                {result.errors.map((error, idx) => {
                                    const styles = getCategoryStyles(error.category);
                                    return (
                                        <div key={idx} style={{
                                            backgroundColor: styles.bg,
                                            border: `1px solid ${styles.border}`,
                                            borderRadius: '12px',
                                            padding: '20px',
                                            position: 'relative'
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: styles.text, fontWeight: 'bold' }}>
                                                    {styles.icon}
                                                    <span>{error.category}</span>
                                                </div>
                                                {error.scene_index !== undefined && onNavigate && (
                                                    <button
                                                        onClick={() => {
                                                            onNavigate(error.scene_index!);
                                                            onClose();
                                                        }}
                                                        style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '4px',
                                                            fontSize: '12px',
                                                            padding: '4px 8px',
                                                            backgroundColor: 'white',
                                                            border: `1px solid ${styles.border}`,
                                                            borderRadius: '6px',
                                                            color: styles.text,
                                                            cursor: 'pointer',
                                                            fontWeight: '600'
                                                        }}
                                                    >
                                                        <MapPin size={14} />
                                                        이동
                                                    </button>
                                                )}
                                            </div>

                                            <div style={{ marginBottom: '12px' }}>
                                                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>감지된 구절</div>
                                                <div style={{ fontStyle: 'italic', color: '#374151', padding: '8px', backgroundColor: 'rgba(255,255,255,0.5)', borderRadius: '6px' }}>
                                                    "{error.violation_point}"
                                                </div>
                                            </div>

                                            <div style={{ marginBottom: '12px' }}>
                                                <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>이유</div>
                                                <p style={{ margin: 0, color: '#1f2937', lineHeight: '1.5' }}>{error.reason}</p>
                                            </div>

                                            <div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: '#16a34a', marginBottom: '4px', fontWeight: 'bold' }}>
                                                    <Lightbulb size={14} />
                                                    수정 제안
                                                </div>
                                                <p style={{ margin: 0, color: '#14532D', lineHeight: '1.5', padding: '8px', backgroundColor: 'rgba(22,163,74,0.05)', borderRadius: '6px' }}>
                                                    {error.suggestion}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : result.status === "설정 파괴 감지" ? (
                            <div style={{ backgroundColor: '#FEF2F2', padding: '16px', borderRadius: '12px', color: '#991B1B' }}>
                                <p style={{ margin: 0 }}>오류 내용이 비어있습니다. 분석 결과를 다시 확인해 주세요.</p>
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', color: '#4B5563', padding: '20px 0' }}>
                                <p style={{ fontSize: '1.1rem', marginBottom: '8px' }}>현재 작성하신 내용에서 기존 설정과 충돌하는 부분이 발견되지 않았습니다.</p>
                                <p style={{ color: '#6b7280' }}>훌륭합니다! 이 기세를 몰아 집필을 이어가세요.</p>
                            </div>
                        )}

                        <button
                            onClick={onClose}
                            style={{
                                width: '100%',
                                marginTop: '24px',
                                padding: '14px',
                                backgroundColor: '#4F46E5',
                                color: 'white',
                                border: 'none',
                                borderRadius: '10px',
                                fontWeight: '600',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                fontSize: '1rem'
                            }}
                            onMouseOver={e => e.currentTarget.style.backgroundColor = '#4338CA'}
                            onMouseOut={e => e.currentTarget.style.backgroundColor = '#4F46E5'}
                        >
                            확인
                        </button>
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', padding: '20px' }}>
                        <p>분석 결과를 불러오지 못했습니다.</p>
                    </div>
                )}
            </div>

            <style>
                {`
                    @keyframes slideUp {
                        from { transform: translateY(20px); opacity: 0; }
                        to { transform: translateY(0); opacity: 1; }
                    }
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                    /* Custom scrollbar for consistency with modern design */
                    div::-webkit-scrollbar {
                        width: 6px;
                    }
                    div::-webkit-scrollbar-track {
                        background: transparent;
                    }
                    div::-webkit-scrollbar-thumb {
                        background: #e2e8f0;
                        border-radius: 10px;
                    }
                    div::-webkit-scrollbar-thumb:hover {
                        background: #cbd5e1;
                    }
                `}
            </style>
        </div>
    );
}
