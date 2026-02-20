import { X, AlertTriangle, CheckCircle, Loader2, Navigation, RefreshCw } from 'lucide-react';

export interface AnalysisResult {
    status: string;
    message?: string;
    results?: Array<{
        type: string;
        quote: string;
        description: string;
        suggestion: string;
    }>;
}

interface AnalysisSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    result: AnalysisResult | null;
    isLoading: boolean;
    onNavigateToQuote?: (quote: string) => void;
    onReanalyze?: () => void;
}

export function AnalysisSidebar({ isOpen, onClose, result, isLoading, onNavigateToQuote, onReanalyze }: AnalysisSidebarProps) {
    if (!isOpen) return null;

    return (
        <div
            style={{
                position: 'fixed',
                bottom: '16px',
                right: '20px',
                width: '450px',
                height: '750px',
                backgroundColor: 'var(--modal-bg)',
                color: 'var(--modal-text)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column',
                borderRadius: '16px',
                border: '1px solid var(--modal-border)',
                animation: 'slideUp 0.3s ease'
            }}
        >
            {/* Header */}
            <div
                style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid var(--modal-border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    backgroundColor: 'var(--modal-header-bg)',
                    color: 'var(--modal-header-text)',
                    borderRadius: '16px 16px 0 0'
                }}
            >
                <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: '600', color: 'inherit' }}>
                    설정 파괴 분석 결과
                </h2>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {/* 재분석 버튼: 결과가 있고 로딩 중이 아닐 때 표시 */}
                    {onReanalyze && result && !isLoading && (
                        <button
                            onClick={onReanalyze}
                            title="재분석"
                            style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                padding: '4px',
                                color: 'inherit',
                                display: 'flex',
                                alignItems: 'center'
                            }}
                        >
                            <RefreshCw size={18} strokeWidth={2.5} />
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            padding: '4px',
                            color: 'inherit'
                        }}
                    >
                        <X size={22} strokeWidth={2.5} />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', backgroundColor: 'var(--modal-bg)', borderRadius: '0 0 16px 16px' }}>
                {isLoading ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px' }}>
                        <Loader2 size={48} strokeWidth={2.5} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} />
                        <p style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem' }}>분석 중입니다...</p>
                    </div>
                ) : result ? (
                    <div>
                        {/* Status Header */}
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px',
                                padding: '16px',
                                borderRadius: '8px',
                                backgroundColor: result.status === '설정 파괴 감지' ? 'rgba(220, 38, 38, 0.1)' : 'rgba(22, 163, 74, 0.1)',
                                marginBottom: '20px',
                                border: '1px solid',
                                borderColor: result.status === '설정 파괴 감지' ? 'rgba(220, 38, 38, 0.2)' : 'rgba(22, 163, 74, 0.2)'
                            }}
                        >
                            {result.status === '설정 파괴 감지' ? (
                                <AlertTriangle size={24} color="#DC2626" strokeWidth={2.5} />
                            ) : (
                                <CheckCircle size={24} color="#16A34A" strokeWidth={2.5} />
                            )}
                            <div>
                                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: result.status === '설정 파괴 감지' ? '#DC2626' : '#16A34A' }}>
                                    {result.status}
                                </h3>
                                {result.message && (
                                    <p style={{ margin: '4px 0 0 0', fontSize: '0.9rem', color: 'var(--muted-foreground)' }}>
                                        {result.message}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* Results List */}
                        {result.results && result.results.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                                {result.results.map((item, index) => (
                                    <div
                                        key={index}
                                        style={{
                                            padding: '16px',
                                            border: '1px solid var(--modal-border)',
                                            borderRadius: '8px',
                                            backgroundColor: 'var(--card)',
                                            color: 'var(--card-foreground)'
                                        }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                            <span
                                                style={{
                                                    fontSize: '0.85rem',
                                                    fontWeight: '600',
                                                    padding: '4px 10px',
                                                    borderRadius: '12px',
                                                    backgroundColor: item.type === '설정 충돌' ? 'rgba(220, 38, 38, 0.1)' : 'rgba(217, 119, 6, 0.1)',
                                                    color: item.type === '설정 충돌' ? '#DC2626' : '#D97706'
                                                }}
                                            >
                                                {item.type}
                                            </span>
                                            {onNavigateToQuote && item.quote && (
                                                <button
                                                    onClick={() => onNavigateToQuote(item.quote)}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '4px',
                                                        padding: '4px 8px',
                                                        fontSize: '0.8rem',
                                                        backgroundColor: 'var(--primary)',
                                                        color: 'var(--primary-foreground)',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    <Navigation size={14} strokeWidth={2.5} />
                                                    이동
                                                </button>
                                            )}
                                        </div>

                                        <div style={{ marginBottom: '12px' }}>
                                            <p style={{ margin: '0 0 4px 0', fontSize: '0.85rem', fontWeight: '600', color: 'var(--modal-text)' }}>
                                                문제 문장:
                                            </p>
                                            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--modal-text)', fontStyle: 'italic', backgroundColor: 'var(--secondary)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                                                "{item.quote}"
                                            </p>
                                        </div>

                                        <div style={{ marginBottom: '12px' }}>
                                            <p style={{ margin: '0 0 4px 0', fontSize: '0.85rem', fontWeight: '600', color: 'var(--modal-text)' }}>
                                                설명:
                                            </p>
                                            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--muted-foreground)', lineHeight: '1.5' }}>
                                                {item.description}
                                            </p>
                                        </div>

                                        <div>
                                            <p style={{ margin: '0 0 4px 0', fontSize: '0.85rem', fontWeight: '600', color: 'var(--modal-text)' }}>
                                                제안:
                                            </p>
                                            <p style={{ margin: 0, fontSize: '0.9rem', color: '#059669', lineHeight: '1.5' }}>
                                                {item.suggestion}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted-foreground)' }}>
                                <CheckCircle size={48} color="#16A34A" strokeWidth={2.5} style={{ margin: '0 auto 16px' }} />
                                <p style={{ fontSize: '1rem', fontWeight: '500' }}>문제가 발견되지 않았습니다!</p>
                                <p style={{ fontSize: '0.9rem', marginTop: '8px' }}>설정이 일관되게 유지되고 있습니다.</p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted-foreground)' }}>
                        <p>분석 결과가 없습니다.</p>
                        <p style={{ fontSize: '0.9rem', marginTop: '8px' }}>설정파괴분석기 버튼을 클릭하여 분석을 시작하세요.</p>
                    </div>
                )}
            </div>

            {/* CSS animations */}
            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
