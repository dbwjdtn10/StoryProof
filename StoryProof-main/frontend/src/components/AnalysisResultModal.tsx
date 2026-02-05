//import React from 'react';
import { ShieldAlert, CheckCircle, X, AlertTriangle, Lightbulb, ArrowRight, Settings } from 'lucide-react';

export interface AnalysisIssue {
    type: string;
    quote: string;
    description: string;
    suggestion: string;
}

export interface AnalysisResult {
    status: string;
    results?: AnalysisIssue[];
    // Legacy support (optional)
    reason?: string;
    suggestion?: string;
    message?: string;
}

interface AnalysisResultModalProps {
    isOpen: boolean;
    onClose: () => void;
    result: AnalysisResult | null;
    isLoading: boolean;
    onNavigate?: (quote: string) => void;
}

export function AnalysisResultModal({ isOpen, onClose, result, isLoading, onNavigate }: AnalysisResultModalProps) {
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
                width: '600px',
                maxWidth: '90%',
                maxHeight: '85vh',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
                position: 'relative',
                animation: 'slideUp 0.3s ease-out',
                overflow: 'hidden'
            }} onClick={e => e.stopPropagation()}>

                <div style={{ padding: '24px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <ShieldAlert size={24} className={isLoading ? 'animate-pulse' : (result?.status === "설정 파괴 감지" ? "text-red-500" : "text-green-500")} />
                        설정 파괴 탐지기
                    </h2>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: '#9ca3af',
                            padding: '4px'
                        }}
                    >
                        <X size={24} />
                    </button>
                </div>

                <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
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

                            {/* Legacy support for old format */}
                            {result.reason && !result.results && (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                    <div style={{ backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px', padding: '16px' }}>
                                        <strong style={{ color: '#991B1B', display: 'block', marginBottom: '4px' }}>감지된 오류</strong>
                                        <p style={{ margin: 0, color: '#7F1D1D' }}>{result.reason}</p>
                                    </div>
                                    <div style={{ backgroundColor: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '12px', padding: '16px' }}>
                                        <strong style={{ color: '#166534', display: 'block', marginBottom: '4px' }}>수정 제안</strong>
                                        <p style={{ margin: 0, color: '#14532D' }}>{result.suggestion}</p>
                                    </div>
                                </div>
                            )}

                            {/* New structured format */}
                            {result.results && result.results.map((issue, idx) => (
                                <div key={idx} style={{
                                    border: '1px solid #e5e7eb',
                                    borderRadius: '12px',
                                    marginBottom: '20px',
                                    overflow: 'hidden',
                                    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                                }}>
                                    <div style={{
                                        backgroundColor: issue.type.includes('설정 충돌') ? '#FEF2F2' : '#FFF7ED',
                                        padding: '12px 16px',
                                        borderBottom: '1px solid #e5e7eb',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center'
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                            {issue.type.includes('설정 충돌') ? (
                                                <AlertTriangle size={18} color="#EF4444" />
                                            ) : (
                                                <Settings size={18} color="#F59E0B" />
                                            )}
                                            <span style={{
                                                fontWeight: 'bold',
                                                color: issue.type.includes('설정 충돌') ? '#991B1B' : '#92400E',
                                                fontSize: '1rem'
                                            }}>
                                                [{issue.type.includes('설정 충돌') ? '⚠️설정 충돌' : '⚙️개연성 경고'}]
                                            </span>
                                        </div>
                                        {onNavigate && issue.quote && (
                                            <button
                                                onClick={() => {
                                                    onNavigate(issue.quote);
                                                    onClose();
                                                }}
                                                style={{
                                                    fontSize: '0.875rem',
                                                    color: '#4F46E5',
                                                    background: 'white',
                                                    border: '1px solid #E0E7FF',
                                                    padding: '4px 10px',
                                                    borderRadius: '6px',
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                    fontWeight: '600'
                                                }}
                                            >
                                                <ArrowRight size={14} />
                                                위치로 이동
                                            </button>
                                        )}
                                    </div>

                                    <div style={{ padding: '16px' }}>
                                        {issue.quote && (
                                            <div style={{
                                                backgroundColor: '#f9fafb',
                                                padding: '12px',
                                                borderRadius: '8px',
                                                fontStyle: 'italic',
                                                color: '#4b5563',
                                                marginBottom: '16px',
                                                borderLeft: '3px solid #d1d5db'
                                            }}>
                                                "{issue.quote}"
                                            </div>
                                        )}

                                        <div style={{ marginBottom: '16px' }}>
                                            <h4 style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#374151', margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                {issue.type.includes('설정 충돌') ? <AlertTriangle size={16} /> : <Settings size={16} />}
                                                {issue.type.includes('설정 충돌') ? '오류 상세' : '개연성 경고 상세'}
                                            </h4>
                                            <p style={{ margin: 0, color: '#4B5563', lineHeight: '1.5' }}>
                                                {issue.description}
                                            </p>
                                        </div>

                                        <div style={{
                                            backgroundColor: '#F0FDF4',
                                            borderRadius: '8px',
                                            padding: '12px'
                                        }}>
                                            <h4 style={{ fontSize: '0.95rem', fontWeight: 'bold', color: '#166534', margin: '0 0 4px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                <Lightbulb size={16} />
                                                [💡수정 제안]
                                            </h4>
                                            <p style={{ margin: 0, color: '#14532D', lineHeight: '1.5' }}>
                                                {issue.suggestion.replace('💡수정 제안:', '').trim()}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {result.status !== "설정 파괴 감지" && (
                                <div style={{ textAlign: 'center', color: '#4B5563' }}>
                                    <p>현재 작성하신 내용에서 기존 설정과 충돌하는 부분이 발견되지 않았습니다.</p>
                                    <p>훌륭합니다! 계속 집필하세요.</p>
                                </div>
                            )}

                        </div>
                    ) : (
                        <div style={{ textAlign: 'center', padding: '20px' }}>
                            <p>분석 결과를 불러오지 못했습니다.</p>
                        </div>
                    )}
                </div>

                <div style={{ padding: '24px', borderTop: '1px solid #e5e7eb' }}>
                    <button
                        onClick={onClose}
                        style={{
                            width: '100%',
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
