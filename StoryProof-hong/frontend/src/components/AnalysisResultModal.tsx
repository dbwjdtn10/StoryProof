import React from 'react';
import { ShieldAlert, CheckCircle, X, AlertTriangle, Lightbulb } from 'lucide-react';

interface AnalysisResult {
    status: string;
    reason?: string;
    suggestion?: string;
    message?: string;
}

interface AnalysisResultModalProps {
    isOpen: boolean;
    onClose: () => void;
    result: AnalysisResult | null;
    isLoading: boolean;
}

export function AnalysisResultModal({ isOpen, onClose, result, isLoading }: AnalysisResultModalProps) {
    if (!isOpen) return null;

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
                width: '500px',
                maxWidth: '90%',
                padding: '32px',
                boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
                position: 'relative',
                animation: 'slideUp 0.3s ease-out'
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
                        color: '#9ca3af'
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
                    <div>
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

                        {result.status === "설정 파괴 감지" ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                <div style={{
                                    backgroundColor: '#FEF2F2',
                                    border: '1px solid #FECACA',
                                    borderRadius: '12px',
                                    padding: '16px'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#991B1B', fontWeight: 'bold' }}>
                                        <AlertTriangle size={18} />
                                        <span>감지된 오류</span>
                                    </div>
                                    <p style={{ margin: 0, color: '#7F1D1D', lineHeight: '1.5', maxHeight: '200px', overflowY: 'auto' }}>
                                        {result.reason}
                                    </p>
                                </div>

                                <div style={{
                                    backgroundColor: '#F0FDF4',
                                    border: '1px solid #BBF7D0',
                                    borderRadius: '12px',
                                    padding: '16px'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#166534', fontWeight: 'bold' }}>
                                        <Lightbulb size={18} />
                                        <span>수정 제안</span>
                                    </div>
                                    <p style={{ margin: 0, color: '#14532D', lineHeight: '1.5', maxHeight: '200px', overflowY: 'auto' }}>
                                        {result.suggestion}
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', color: '#4B5563' }}>
                                <p>현재 작성하신 내용에서 기존 설정과 충돌하는 부분이 발견되지 않았습니다.</p>
                                <p>훌륭합니다! 계속 집필하세요.</p>
                            </div>
                        )}

                        <button
                            onClick={onClose}
                            style={{
                                width: '100%',
                                marginTop: '24px',
                                padding: '12px',
                                backgroundColor: '#4F46E5',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                fontWeight: '600',
                                cursor: 'pointer',
                                transition: 'background-color 0.2s'
                            }}
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
                `}
            </style>
        </div>
    );
}
