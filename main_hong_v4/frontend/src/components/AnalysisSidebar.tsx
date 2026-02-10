import { useState, useEffect } from 'react';
import { ShieldAlert, CheckCircle, AlertTriangle, Lightbulb, ArrowRight, Settings, X, Loader, ChevronDown, ChevronRight } from 'lucide-react';

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

interface AnalysisSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    result: AnalysisResult | null;
    isLoading: boolean;
    onNavigate?: (quote: string) => void;
}

export function AnalysisSidebar({ isOpen, onClose, result, isLoading, onNavigate }: AnalysisSidebarProps) {
    const [isConflictsOpen, setIsConflictsOpen] = useState(true);
    const [isWarningsOpen, setIsWarningsOpen] = useState(true);
    const [width, setWidth] = useState(400);
    const [isResizing, setIsResizing] = useState(false);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isResizing) return;
            const newWidth = window.innerWidth - e.clientX;
            if (newWidth >= 300 && newWidth <= 800) {
                setWidth(newWidth);
            }
        };

        const handleMouseUp = () => {
            setIsResizing(false);
        };

        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'ew-resize';
            document.body.style.userSelect = 'none';
        } else {
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';
        }

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';
        };
    }, [isResizing]);

    const conflicts = result?.results?.filter(issue => issue.type.includes('설정 충돌')) || [];
    const warnings = result?.results?.filter(issue => !issue.type.includes('설정 충돌')) || [];

    return (
        <div
            className={`analysis-sidebar ${isOpen ? 'open' : 'closed'}`}
            style={{ width: isOpen ? `${width}px` : undefined }}
        >
            <div
                onMouseDown={() => setIsResizing(true)}
                style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: '6px',
                    cursor: 'ew-resize',
                    backgroundColor: isResizing ? '#4F46E5' : 'transparent',
                    zIndex: 50,
                    transition: 'background-color 0.2s',
                }}
                className="resize-handle"
            />
            <div className="analysis-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert size={20} className={isLoading ? 'animate-pulse' : (result?.status === "설정 파괴 감지" ? "text-red-500" : "text-green-500")} />
                    <h3 className="section-title">설정 파괴 탐지기</h3>
                </div>
                <button onClick={onClose} className="close-button">
                    <X size={20} />
                </button>
            </div>

            <div className="analysis-content">
                {isLoading ? (
                    <div className="analysis-loading">
                        <Loader className="animate-spin" size={32} color="#4F46E5" />
                        <h4 style={{ marginTop: '16px', marginBottom: '8px', color: '#1f2937' }}>설정 파괴 분석 중...</h4>
                        <p style={{ fontSize: '0.875rem', color: '#6b7280', lineHeight: '1.5' }}>
                            AI가 소설의 설정 오류를 정밀하게 검사하고 있습니다.<br />
                            잠시만 기다려주세요.
                        </p>
                    </div>
                ) : result ? (
                    <div className="analysis-results">
                        <div className={`result-summary ${conflicts.length > 0 ? "error" : (warnings.length > 0 ? "warning" : "success")}`}
                            style={warnings.length > 0 && conflicts.length === 0 ? {
                                backgroundColor: '#FFFBEB',
                                border: '1px solid #FDE68A',
                                color: '#D97706'
                            } : undefined}>
                            {conflicts.length > 0 ? (
                                <>
                                    <div className="status-icon error">
                                        <ShieldAlert size={24} />
                                    </div>
                                    <h4 className="status-text">설정 오류 감지됨</h4>
                                </>
                            ) : warnings.length > 0 ? (
                                <>
                                    <div className="status-icon warning" style={{ backgroundColor: '#FDE68A', color: '#D97706' }}>
                                        <AlertTriangle size={24} />
                                    </div>
                                    <h4 className="status-text" style={{ color: '#92400E' }}>개연성 경고 감지됨</h4>
                                </>
                            ) : (
                                <>
                                    <div className="status-icon success">
                                        <CheckCircle size={24} />
                                    </div>
                                    <h4 className="status-text">설정이 완벽합니다!</h4>
                                </>
                            )}
                        </div>

                        {/* Conflicts Section */}
                        {conflicts.length > 0 && (
                            <div className="section-group">
                                <button
                                    onClick={() => setIsConflictsOpen(!isConflictsOpen)}
                                    className={`section-header conflict ${isConflictsOpen ? 'open' : ''}`}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        width: '100%',
                                        padding: '12px 16px',
                                        backgroundColor: '#FEF2F2',
                                        border: '1px solid #FECACA',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        marginTop: '16px',
                                        marginBottom: '8px',
                                        color: '#DC2626'
                                    }}
                                >
                                    {isConflictsOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    <span style={{ marginLeft: '8px', fontWeight: '600', flex: 1, textAlign: 'left' }}>
                                        ⚠️ 설정 충돌 ({conflicts.length})
                                    </span>
                                </button>

                                {isConflictsOpen && (
                                    <div className="section-content">
                                        {conflicts.map((issue, idx) => (
                                            <IssueCard key={idx} issue={issue} onNavigate={onNavigate} isConflict={true} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Warnings Section */}
                        {warnings.length > 0 && (
                            <div className="section-group">
                                <button
                                    onClick={() => setIsWarningsOpen(!isWarningsOpen)}
                                    className={`section-header warning ${isWarningsOpen ? 'open' : ''}`}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        width: '100%',
                                        padding: '12px 16px',
                                        backgroundColor: '#FFFBEB',
                                        border: '1px solid #FDE68A',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        marginTop: '16px',
                                        marginBottom: '8px',
                                        color: '#D97706'
                                    }}
                                >
                                    {isWarningsOpen ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    <span style={{ marginLeft: '8px', fontWeight: '600', flex: 1, textAlign: 'left' }}>
                                        ⚙️ 개연성 경고 ({warnings.length})
                                    </span>
                                </button>

                                {isWarningsOpen && (
                                    <div className="section-content">
                                        {warnings.map((issue, idx) => (
                                            <IssueCard key={idx} issue={issue} onNavigate={onNavigate} isConflict={false} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {result.status !== "설정 파괴 감지" && conflicts.length === 0 && warnings.length === 0 && (
                            <div className="empty-state">
                                <p>현재 작성하신 내용에서 기존 설정과 충돌하는 부분이 발견되지 않았습니다.</p>
                                <p>훌륭합니다! 계속 집필하세요.</p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="empty-state">
                        <p>분석 결과를 기다리는 중...</p>
                    </div>
                )}
            </div>

            <style>{`
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .animate-spin {
                    animation: spin 1s linear infinite;
                }
                .animate-pulse {
                    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: .5; }
                }
                .resize-handle:hover {
                    background-color: #E0E7FF !important;
                }
            `}</style>
        </div>
    );
}

function IssueCard({ issue, onNavigate, isConflict }: { issue: AnalysisIssue, onNavigate?: (quote: string) => void, isConflict: boolean }) {
    return (
        <div className="issue-card" style={{ marginBottom: '16px', overflow: 'hidden' }}>
            <div className={`issue-header ${isConflict ? 'conflict' : 'warning'}`}>
                <div className="issue-type">
                    {isConflict ? (
                        <AlertTriangle size={16} color="#EF4444" />
                    ) : (
                        <Settings size={16} color="#F59E0B" />
                    )}
                    <span>
                        [{isConflict ? '⚠️설정 충돌' : '⚙️개연성 경고'}]
                    </span>
                </div>
                {onNavigate && issue.quote && (
                    <button
                        className="navigate-button"
                        onClick={() => onNavigate(issue.quote)}
                        title="해당 문장으로 이동"
                    >
                        <ArrowRight size={14} />
                    </button>
                )}
            </div>

            <div className="issue-body" style={{ padding: '0 16px 16px 16px' }}>
                {issue.quote && (
                    <div className="quoted-text" style={{
                        marginTop: '12px',
                        padding: '12px',
                        backgroundColor: '#F9FAFB',
                        borderLeft: '4px solid #D1D5DB',
                        fontStyle: 'italic',
                        color: '#4B5563',
                        fontSize: '0.9rem'
                    }}>
                        "{issue.quote}"
                    </div>
                )}

                <div className="issue-detail" style={{ marginTop: '16px' }}>
                    <h4 style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        color: isConflict ? '#B91C1C' : '#92400E',
                        marginBottom: '8px'
                    }}>
                        {isConflict ? <AlertTriangle size={14} /> : <Settings size={14} />}
                        {isConflict ? '오류 상세 (Problem)' : '개연성 경고 (Issue)'}
                    </h4>
                    <div style={{
                        fontSize: '1.2rem',
                        color: '#374151',
                        lineHeight: '1.6',
                        whiteSpace: 'pre-wrap'
                    }}>
                        {formatToParagraphs(issue.description)}
                    </div>
                </div>

                <div className="issue-suggestion" style={{
                    marginTop: '16px',
                    backgroundColor: isConflict ? '#FEF2F2' : '#FFFBEB',
                    padding: '12px',
                    borderRadius: '8px',
                    border: isConflict ? '1px solid #FECACA' : '1px solid #FDE68A'
                }}>
                    <h4 style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '0.9rem',
                        fontWeight: '600',
                        color: isConflict ? '#B91C1C' : '#92400E',
                        marginBottom: '8px'
                    }}>
                        <Lightbulb size={14} />
                        수정 제안 (Solution)
                    </h4>
                    <div style={{
                        fontSize: '1.2rem',
                        color: '#1F2937',
                        lineHeight: '1.6',
                        whiteSpace: 'pre-wrap'
                    }}>
                        {formatToParagraphs(issue.suggestion.replace('💡수정 제안:', '').trim())}
                    </div>
                </div>
            </div>
        </div>
    );
}

function formatToParagraphs(text: string) {
    if (!text) return null;

    // Split by period, question mark, or exclamation mark followed by a space or end of string.
    // Use positive lookbehind to keep the punctuation with the sentence.
    const sentences = text.split(/(?<=[.?!])\s+/).filter(s => s.trim().length > 0);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {sentences.map((sentence, idx) => (
                <p key={idx} style={{ margin: 0 }}>{sentence}</p>
            ))}
        </div>
    );
}
