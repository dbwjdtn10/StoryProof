import { useState, useEffect } from 'react';
import { X, AlertTriangle, CheckCircle, Loader2, Navigation, RefreshCw, ChevronDown, Copy, BarChart3, Pen, BookOpen, ClipboardCopy } from 'lucide-react';
import { toast } from 'sonner';

/** A generic issue with description and optional suggestion */
interface AnalysisIssue {
    description: string;
    suggestion?: string;
}

interface AnalysisEvaluation {
    score?: number;
    strengths?: string[];
    weaknesses?: string[];
}

interface StructureSection {
    name: string;
    description: string;
}

interface AnalysisStructure {
    type: string;
    sections?: StructureSection[];
}

interface AnalysisConflict {
    type: string;
    intensity: number;
    description: string;
}

interface AnalysisPacing {
    overall: string;
    issues?: AnalysisIssue[];
}

interface AnalysisForeshadowing {
    type: string;
    description: string;
}

interface AnalysisTone {
    primary: string;
    consistency: string;
    issues?: AnalysisIssue[];
}

interface AnalysisSentenceStructure {
    dialogue_ratio: string;
    avg_length: string;
    issues?: AnalysisIssue[];
}

interface VocabularyRepetition {
    word: string;
    count: number;
    alternatives?: string[];
}

interface VocabularyCliche {
    expression: string;
    suggestion?: string;
}

interface AnalysisVocabulary {
    diversity: string;
    repetitions?: VocabularyRepetition[];
    cliches?: VocabularyCliche[];
}

interface AnalysisPointOfView {
    type: string;
    consistency: string;
    issues?: AnalysisIssue[];
}

export interface PlotAnalysisData {
    structure?: AnalysisStructure;
    conflicts?: AnalysisConflict[];
    pacing?: AnalysisPacing;
    foreshadowing?: AnalysisForeshadowing[];
    evaluation?: AnalysisEvaluation;
    error?: string;
}

export interface StyleAnalysisData {
    tone?: AnalysisTone;
    sentence_structure?: AnalysisSentenceStructure;
    vocabulary?: AnalysisVocabulary;
    point_of_view?: AnalysisPointOfView;
    evaluation?: AnalysisEvaluation;
    error?: string;
}

export interface AnalysisResult {
    status: string;
    message?: string;
    results?: Array<{
        type: string;
        severity?: string;
        quote: string;
        evidence?: string;
        description: string;
        suggestion: string;
    }>;
    // Plot analysis fields
    structure?: AnalysisStructure;
    conflicts?: AnalysisConflict[];
    pacing?: AnalysisPacing;
    foreshadowing?: AnalysisForeshadowing[];
    // Style analysis fields
    tone?: AnalysisTone;
    sentence_structure?: AnalysisSentenceStructure;
    vocabulary?: AnalysisVocabulary;
    point_of_view?: AnalysisPointOfView;
    // Common
    evaluation?: AnalysisEvaluation;
    // Overall (combined)
    plot?: PlotAnalysisData;
    style?: StyleAnalysisData;
    // Error
    error?: string;
}

interface AnalysisSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    result: AnalysisResult | null;
    isLoading: boolean;
    isCachedResult?: boolean;
    onNavigateToQuote?: (quote: string) => void;
    onReanalyze?: () => void;
    onApplySuggestion?: (original: string, suggestion: string) => void;
    analysisType?: string;
}

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; label: string; icon: string }> = {
    '치명적': { color: '#DC2626', bg: 'rgba(220, 38, 38, 0.1)', label: '치명적', icon: '✗' },
    '주의': { color: '#D97706', bg: 'rgba(217, 119, 6, 0.1)', label: '주의', icon: '⚠' },
    '참고': { color: '#2563EB', bg: 'rgba(37, 99, 235, 0.1)', label: '참고', icon: '✓' },
};

function SeverityBadge({ severity }: { severity?: string }) {
    const config = severity ? SEVERITY_CONFIG[severity] : null;
    if (!config) return null;
    return (
        <span style={{
            fontSize: '0.75rem', fontWeight: '700', padding: '2px 8px', borderRadius: '10px',
            backgroundColor: config.bg, color: config.color, marginLeft: '6px'
        }}>
            {config.icon} {config.label}
        </span>
    );
}

function ScoreGauge({ score }: { score: number }) {
    const color = score >= 80 ? '#16A34A' : score >= 60 ? '#D97706' : '#DC2626';
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 0' }}>
            <div style={{ position: 'relative', width: '56px', height: '56px' }}>
                <svg width="56" height="56" viewBox="0 0 56 56">
                    <circle cx="28" cy="28" r="24" fill="none" stroke="var(--border)" strokeWidth="5" />
                    <circle cx="28" cy="28" r="24" fill="none" stroke={color} strokeWidth="5"
                        strokeDasharray={`${(score / 100) * 150.8} 150.8`}
                        strokeLinecap="round"
                        transform="rotate(-90 28 28)" />
                </svg>
                <span style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '0.9rem', fontWeight: '700', color }}>{score}</span>
            </div>
            <span style={{ fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>/ 100</span>
        </div>
    );
}

function ConsistencyRenderer({ result, onNavigateToQuote, onApplySuggestion, filter }: {
    result: AnalysisResult; onNavigateToQuote?: (q: string) => void; onApplySuggestion?: (o: string, s: string) => void; filter: string;
}) {
    const items = (result.results || []).filter(item => filter === 'all' || item.severity === filter);
    return (
        <div>
            {/* Status Header */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', borderRadius: '8px',
                backgroundColor: result.status === '설정 파괴 감지' ? 'rgba(220, 38, 38, 0.1)' : 'rgba(22, 163, 74, 0.1)',
                marginBottom: '16px', border: '1px solid',
                borderColor: result.status === '설정 파괴 감지' ? 'rgba(220, 38, 38, 0.2)' : 'rgba(22, 163, 74, 0.2)'
            }}>
                {result.status === '설정 파괴 감지' ? (
                    <AlertTriangle size={24} color="#DC2626" strokeWidth={2.5} />
                ) : (
                    <CheckCircle size={24} color="#16A34A" strokeWidth={2.5} />
                )}
                <div>
                    <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '600', color: result.status === '설정 파괴 감지' ? '#DC2626' : '#16A34A' }}>
                        {result.status}
                    </h3>
                    {result.results && result.results.length > 0 && (
                        <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>{result.results.length}건 발견</span>
                    )}
                </div>
            </div>

            {items.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {items.map((item, index) => (
                        <div key={index} style={{ padding: '14px', border: '1px solid var(--modal-border)', borderRadius: '8px', backgroundColor: 'var(--card)', color: 'var(--card-foreground)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <span style={{
                                        fontSize: '0.8rem', fontWeight: '600', padding: '3px 10px', borderRadius: '12px',
                                        backgroundColor: item.type === '설정 충돌' ? 'rgba(220, 38, 38, 0.1)' : 'rgba(217, 119, 6, 0.1)',
                                        color: item.type === '설정 충돌' ? '#DC2626' : '#D97706'
                                    }}>{item.type}</span>
                                    <SeverityBadge severity={item.severity} />
                                </div>
                                {onNavigateToQuote && item.quote && (
                                    <button onClick={() => onNavigateToQuote(item.quote)} style={{
                                        display: 'flex', alignItems: 'center', gap: '4px', padding: '3px 8px', fontSize: '0.75rem',
                                        backgroundColor: 'var(--primary)', color: 'var(--primary-foreground)', border: 'none', borderRadius: '4px', cursor: 'pointer'
                                    }}>
                                        <Navigation size={12} strokeWidth={2.5} /> 이동
                                    </button>
                                )}
                            </div>

                            <div style={{ marginBottom: '10px' }}>
                                <p style={{ margin: '0 0 4px 0', fontSize: '0.8rem', fontWeight: '600', color: 'var(--modal-text)' }}>문제 문장:</p>
                                <p style={{ margin: 0, fontSize: '0.85rem', fontStyle: 'italic', backgroundColor: 'var(--secondary)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)', color: 'var(--modal-text)' }}>
                                    "{item.quote}"
                                </p>
                            </div>

                            {item.evidence && (
                                <div style={{ marginBottom: '10px' }}>
                                    <p style={{ margin: '0 0 4px 0', fontSize: '0.8rem', fontWeight: '600', color: 'var(--modal-text)' }}>근거:</p>
                                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)', lineHeight: '1.5' }}>{item.evidence}</p>
                                </div>
                            )}

                            <div style={{ marginBottom: '10px' }}>
                                <p style={{ margin: '0 0 4px 0', fontSize: '0.8rem', fontWeight: '600', color: 'var(--modal-text)' }}>설명:</p>
                                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--muted-foreground)', lineHeight: '1.5' }}>{item.description}</p>
                            </div>

                            <div>
                                <p style={{ margin: '0 0 4px 0', fontSize: '0.8rem', fontWeight: '600', color: 'var(--modal-text)' }}>제안:</p>
                                <p style={{ margin: 0, fontSize: '0.85rem', color: '#059669', lineHeight: '1.5' }}>{item.suggestion}</p>
                                {onApplySuggestion && item.quote && item.suggestion && (
                                    <button onClick={() => onApplySuggestion(item.quote, item.suggestion)} style={{
                                        marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 10px', fontSize: '0.75rem',
                                        backgroundColor: 'rgba(5, 150, 105, 0.1)', color: '#059669', border: '1px solid rgba(5, 150, 105, 0.3)',
                                        borderRadius: '4px', cursor: 'pointer'
                                    }}>
                                        <Copy size={12} /> 제안 적용
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div style={{ textAlign: 'center', padding: '30px 20px', color: 'var(--muted-foreground)' }}>
                    <CheckCircle size={40} color="#16A34A" strokeWidth={2.5} style={{ margin: '0 auto 12px' }} />
                    <p style={{ fontSize: '0.95rem', fontWeight: '500' }}>문제가 발견되지 않았습니다!</p>
                </div>
            )}
        </div>
    );
}

function PlotRenderer({ data }: { data: PlotAnalysisData | undefined }) {
    if (!data || data.error) return <p style={{ color: 'var(--muted-foreground)' }}>플롯 분석 데이터가 없습니다.</p>;
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {data.evaluation?.score != null && <ScoreGauge score={data.evaluation.score} />}

            {/* Structure */}
            {data.structure && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>구조: {data.structure.type}</h4>
                    {(data.structure.sections || []).map((s: StructureSection, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', backgroundColor: 'var(--secondary)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <strong>{s.name}</strong>: {s.description}
                        </div>
                    ))}
                </div>
            )}

            {/* Conflicts */}
            {data.conflicts && data.conflicts.length > 0 && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>갈등 요소</h4>
                    {data.conflicts.map((c: AnalysisConflict, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <span style={{ padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(220, 38, 38, 0.1)', color: '#DC2626', fontSize: '0.75rem', fontWeight: '600' }}>{c.type}</span>
                            <span style={{ marginLeft: '6px', fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>강도: {c.intensity}/10</span>
                            <p style={{ margin: '6px 0 0', color: 'var(--muted-foreground)' }}>{c.description}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Pacing */}
            {data.pacing && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>전개 속도: {data.pacing.overall}</h4>
                    {(data.pacing.issues || []).map((p: AnalysisIssue, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <p style={{ margin: '0 0 4px', fontWeight: '500' }}>{p.description}</p>
                            {p.suggestion && <p style={{ margin: 0, color: '#059669', fontSize: '0.8rem' }}>{'->'} {p.suggestion}</p>}
                        </div>
                    ))}
                </div>
            )}

            {/* Foreshadowing */}
            {data.foreshadowing && data.foreshadowing.length > 0 && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>복선/떡밥</h4>
                    {data.foreshadowing.map((f: AnalysisForeshadowing, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', backgroundColor: 'var(--secondary)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <span style={{ padding: '2px 6px', borderRadius: '4px', backgroundColor: f.type === '회수됨' ? 'rgba(22, 163, 74, 0.1)' : f.type === '신규' ? 'rgba(37, 99, 235, 0.1)' : 'rgba(217, 119, 6, 0.1)', color: f.type === '회수됨' ? '#16A34A' : f.type === '신규' ? '#2563EB' : '#D97706', fontSize: '0.75rem', fontWeight: '600' }}>{f.type}</span>
                            <p style={{ margin: '6px 0 0', color: 'var(--muted-foreground)' }}>{f.description}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Evaluation */}
            {data.evaluation && (
                <div>
                    {(data.evaluation.strengths?.length ?? 0) > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                            <p style={{ margin: '0 0 4px', fontSize: '0.8rem', fontWeight: '600', color: '#16A34A' }}>강점</p>
                            {data.evaluation.strengths?.map((s: string, i: number) => <p key={i} style={{ margin: '2px 0', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>+ {s}</p>)}
                        </div>
                    )}
                    {(data.evaluation.weaknesses?.length ?? 0) > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                            <p style={{ margin: '0 0 4px', fontSize: '0.8rem', fontWeight: '600', color: '#DC2626' }}>약점</p>
                            {data.evaluation.weaknesses?.map((w: string, i: number) => <p key={i} style={{ margin: '2px 0', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>- {w}</p>)}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function StyleRenderer({ data }: { data: StyleAnalysisData | undefined }) {
    if (!data || data.error) return <p style={{ color: 'var(--muted-foreground)' }}>문체 분석 데이터가 없습니다.</p>;
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {data.evaluation?.score != null && <ScoreGauge score={data.evaluation.score} />}

            {/* Tone */}
            {data.tone && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>어조: {data.tone.primary} ({data.tone.consistency})</h4>
                    {(data.tone.issues || []).map((t: AnalysisIssue, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <p style={{ margin: '0 0 4px' }}>{t.description}</p>
                            {t.suggestion && <p style={{ margin: 0, color: '#059669', fontSize: '0.8rem' }}>{'->'} {t.suggestion}</p>}
                        </div>
                    ))}
                </div>
            )}

            {/* Sentence Structure */}
            {data.sentence_structure && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>문장 구조</h4>
                    <p style={{ margin: '0 0 4px', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>대화문 비율: {data.sentence_structure.dialogue_ratio}</p>
                    <p style={{ margin: '0 0 8px', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>평균 문장 길이: {data.sentence_structure.avg_length}</p>
                    {(data.sentence_structure.issues || []).map((s: AnalysisIssue, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <p style={{ margin: '0 0 4px' }}>{s.description}</p>
                            {s.suggestion && <p style={{ margin: 0, color: '#059669', fontSize: '0.8rem' }}>{'->'} {s.suggestion}</p>}
                        </div>
                    ))}
                </div>
            )}

            {/* Vocabulary */}
            {data.vocabulary && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>어휘 다양성: {data.vocabulary.diversity}</h4>
                    {(data.vocabulary.repetitions || []).map((r: VocabularyRepetition, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', backgroundColor: 'var(--secondary)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <strong>"{r.word}"</strong> ({r.count}회) {'->'} 대안: {(r.alternatives || []).join(', ')}
                        </div>
                    ))}
                    {(data.vocabulary.cliches || []).map((c: VocabularyCliche, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <span style={{ color: '#D97706' }}>클리셰:</span> "{c.expression}"
                            {c.suggestion && <p style={{ margin: '4px 0 0', color: '#059669', fontSize: '0.8rem' }}>{'->'} {c.suggestion}</p>}
                        </div>
                    ))}
                </div>
            )}

            {/* POV */}
            {data.point_of_view && (
                <div>
                    <h4 style={{ margin: '0 0 8px', fontSize: '0.9rem', fontWeight: '600', color: 'var(--modal-text)' }}>서술 시점: {data.point_of_view.type} ({data.point_of_view.consistency})</h4>
                    {(data.point_of_view.issues || []).map((p: AnalysisIssue, i: number) => (
                        <div key={i} style={{ padding: '8px', marginBottom: '6px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '0.85rem' }}>
                            <p style={{ margin: '0 0 4px' }}>{p.description}</p>
                            {p.suggestion && <p style={{ margin: 0, color: '#059669', fontSize: '0.8rem' }}>{'->'} {p.suggestion}</p>}
                        </div>
                    ))}
                </div>
            )}

            {/* Evaluation */}
            {data.evaluation && (
                <div>
                    {(data.evaluation.strengths?.length ?? 0) > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                            <p style={{ margin: '0 0 4px', fontSize: '0.8rem', fontWeight: '600', color: '#16A34A' }}>강점</p>
                            {data.evaluation.strengths?.map((s: string, i: number) => <p key={i} style={{ margin: '2px 0', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>+ {s}</p>)}
                        </div>
                    )}
                    {(data.evaluation.weaknesses?.length ?? 0) > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                            <p style={{ margin: '0 0 4px', fontSize: '0.8rem', fontWeight: '600', color: '#DC2626' }}>약점</p>
                            {data.evaluation.weaknesses?.map((w: string, i: number) => <p key={i} style={{ margin: '2px 0', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>- {w}</p>)}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

const ANALYSIS_TYPE_LABELS: Record<string, { label: string; icon: typeof AlertTriangle }> = {
    consistency: { label: '설정 파괴 분석', icon: AlertTriangle },
    plot: { label: '플롯 분석', icon: BarChart3 },
    style: { label: '문체 분석', icon: Pen },
    overall: { label: '종합 분석', icon: BookOpen },
};

export function AnalysisSidebar({ isOpen, onClose, result, isLoading, isCachedResult, onNavigateToQuote, onReanalyze, onApplySuggestion, analysisType = 'consistency' }: AnalysisSidebarProps) {
    const [severityFilter, setSeverityFilter] = useState('all');

    // ESC 키로 사이드바 닫기
    useEffect(() => {
        if (!isOpen) return;
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const typeConfig = ANALYSIS_TYPE_LABELS[analysisType] || ANALYSIS_TYPE_LABELS.consistency;
    const TypeIcon = typeConfig.icon;

    const renderContent = () => {
        if (isLoading) {
            return (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px' }}>
                    <Loader2 size={48} strokeWidth={2.5} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} />
                    <p style={{ color: 'var(--muted-foreground)', fontSize: '0.95rem' }}>분석 중입니다...</p>
                </div>
            );
        }

        if (!result) {
            return (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted-foreground)' }}>
                    <p>분석 결과가 없습니다.</p>
                    <p style={{ fontSize: '0.9rem', marginTop: '8px' }}>분석 버튼을 클릭하여 분석을 시작하세요.</p>
                </div>
            );
        }

        if (result.error) {
            return (
                <div style={{ textAlign: 'center', padding: '40px 20px', color: '#DC2626' }}>
                    <AlertTriangle size={40} style={{ margin: '0 auto 12px' }} />
                    <p>분석 중 오류가 발생했습니다.</p>
                    <p style={{ fontSize: '0.85rem', marginTop: '8px', color: 'var(--muted-foreground)' }}>{result.error}</p>
                </div>
            );
        }

        switch (analysisType) {
            case 'consistency':
                return <ConsistencyRenderer result={result} onNavigateToQuote={onNavigateToQuote} onApplySuggestion={onApplySuggestion} filter={severityFilter} />;
            case 'plot':
                return <PlotRenderer data={result} />;
            case 'style':
                return <StyleRenderer data={result} />;
            case 'overall':
                return (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        {result.evaluation?.score != null && <ScoreGauge score={result.evaluation.score} />}
                        {(result.evaluation?.strengths?.length ?? 0) > 0 && (
                            <div>
                                <p style={{ margin: '0 0 4px', fontSize: '0.8rem', fontWeight: '600', color: '#16A34A' }}>강점</p>
                                {result.evaluation?.strengths?.map((s: string, i: number) => <p key={i} style={{ margin: '2px 0', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>+ {s}</p>)}
                            </div>
                        )}
                        {(result.evaluation?.weaknesses?.length ?? 0) > 0 && (
                            <div>
                                <p style={{ margin: '0 0 4px', fontSize: '0.8rem', fontWeight: '600', color: '#DC2626' }}>약점</p>
                                {result.evaluation?.weaknesses?.map((w: string, i: number) => <p key={i} style={{ margin: '2px 0', fontSize: '0.85rem', color: 'var(--muted-foreground)' }}>- {w}</p>)}
                            </div>
                        )}
                        <h3 style={{ margin: '8px 0 0', fontSize: '1rem', fontWeight: '600', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>플롯 분석</h3>
                        <PlotRenderer data={result.plot} />
                        <h3 style={{ margin: '8px 0 0', fontSize: '1rem', fontWeight: '600', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>문체 분석</h3>
                        <StyleRenderer data={result.style} />
                    </div>
                );
            default:
                return <ConsistencyRenderer result={result} onNavigateToQuote={onNavigateToQuote} onApplySuggestion={onApplySuggestion} filter={severityFilter} />;
        }
    };

    return (
        <div
            style={{
                position: 'fixed',
                bottom: window.innerWidth <= 640 ? '0' : '16px',
                right: window.innerWidth <= 640 ? '0' : '20px',
                width: window.innerWidth <= 640 ? '100%' : '450px',
                height: window.innerWidth <= 640 ? '100%' : '750px',
                maxHeight: '100dvh',
                borderRadius: window.innerWidth <= 640 ? '0' : '16px',
                backgroundColor: 'var(--modal-bg)', color: 'var(--modal-text)',
                boxShadow: '0 8px 32px rgba(0,0,0,0.15)', zIndex: 1000,
                display: 'flex', flexDirection: 'column',
                border: window.innerWidth <= 640 ? 'none' : '1px solid var(--modal-border)', animation: 'slideUp 0.3s ease'
            }}
        >
            {/* Header */}
            <div style={{
                padding: '16px 20px', borderBottom: '1px solid var(--modal-border)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                backgroundColor: 'var(--modal-header-bg)', color: 'var(--modal-header-text)',
                borderRadius: '16px 16px 0 0'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <TypeIcon size={18} strokeWidth={2.5} />
                    <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600', color: 'inherit' }}>{typeConfig.label}</h2>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {result && !isLoading && (
                        <button onClick={() => {
                            const text = JSON.stringify(result, null, 2);
                            navigator.clipboard.writeText(text).then(() => toast.success('분석 결과가 복사되었습니다.'));
                        }} title="결과 복사" aria-label="결과 복사" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'inherit', display: 'flex', alignItems: 'center' }}>
                            <ClipboardCopy size={18} strokeWidth={2.5} />
                        </button>
                    )}
                    {onReanalyze && result && !isLoading && (
                        <button onClick={onReanalyze} title="재분석" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'inherit', display: 'flex', alignItems: 'center' }}>
                            <RefreshCw size={18} strokeWidth={2.5} />
                        </button>
                    )}
                    <button onClick={onClose} aria-label="닫기" title="닫기" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'inherit' }}>
                        <X size={22} strokeWidth={2.5} />
                    </button>
                </div>
            </div>

            {/* Severity filter (consistency only) */}
            {analysisType === 'consistency' && result && result.results && result.results.length > 0 && !isLoading && (
                <div style={{ padding: '8px 20px', borderBottom: '1px solid var(--modal-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>필터:</span>
                    <div style={{ position: 'relative' }}>
                        <select
                            value={severityFilter}
                            onChange={(e) => setSeverityFilter(e.target.value)}
                            style={{
                                appearance: 'none', fontSize: '0.8rem', padding: '4px 24px 4px 8px',
                                border: '1px solid var(--border)', borderRadius: '4px',
                                backgroundColor: 'var(--card)', color: 'var(--card-foreground)', cursor: 'pointer'
                            }}
                        >
                            <option value="all">전체</option>
                            <option value="치명적">치명적</option>
                            <option value="주의">주의</option>
                            <option value="참고">참고</option>
                        </select>
                        <ChevronDown size={12} style={{ position: 'absolute', right: '6px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--muted-foreground)' }} />
                    </div>
                </div>
            )}

            {/* Cached result banner */}
            {isCachedResult && result && !isLoading && (
                <div style={{
                    padding: '10px 20px', borderBottom: '1px solid var(--modal-border)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    backgroundColor: (() => {
                        const t = document.documentElement.getAttribute('data-theme') || 'light';
                        return t === 'dark' ? '#1a1a1a' : 'rgba(59, 130, 246, 0.08)';
                    })()
                }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
                        이전 분석 결과입니다
                    </span>
                    {onReanalyze && (
                        <button
                            onClick={onReanalyze}
                            style={{
                                fontSize: '0.8rem', padding: '4px 12px', borderRadius: '6px',
                                border: '1px solid var(--primary)',
                                backgroundColor: (() => {
                                    const t = document.documentElement.getAttribute('data-theme') || 'light';
                                    return t === 'dark' ? '#000000' : 'var(--primary)';
                                })(),
                                color: 'white', cursor: 'pointer', fontWeight: '500'
                            }}
                        >
                            새로 분석하기
                        </button>
                    )}
                </div>
            )}

            {/* Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', backgroundColor: 'var(--modal-bg)', borderRadius: '0 0 16px 16px' }}>
                {renderContent()}
            </div>

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
