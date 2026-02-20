import { MessageCircle, X, Send, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { askQuestionStream, ChatAnswerResponse, StreamMeta } from '../api/chat';
import '../chatbot.css';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    isStreaming?: boolean;
    source?: {
        filename: string;
        scene_index?: number;
        chapter_id?: number;
        summary?: string;
        total_scenes: number;
    } | null;
    similarity?: number;
}



function ChatMessageItem({ msg, onNavigateToScene, chapterId }: { msg: Message, onNavigateToScene?: (idx: number) => void, chapterId?: number }) {
    const [isSourceOpen, setIsSourceOpen] = useState(false);
    const [isDetailOpen, setIsDetailOpen] = useState(false);

    let mainContent = msg.content;
    let detailContent = '';

    if (msg.role === 'assistant' && msg.content.includes('[상세 설명]')) {
        const parts = msg.content.split('[상세 설명]');
        mainContent = parts[0].replace('[핵심 요약]', '').trim();
        detailContent = parts[1].trim();
    }

    return (
        <div className={`chatbot-message ${msg.role}`} style={{ marginBottom: '1rem', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div className={`chatbot-message-bubble ${msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`} style={{
                padding: '0.75rem 1rem',
                borderRadius: '1.5rem',
                maxWidth: '100%',
            }}>
                <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{mainContent}</p>

                {detailContent && (
                    <div className="detail-container" style={{ marginTop: '0.5rem', borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: '0.5rem' }}>
                        <button
                            onClick={() => setIsDetailOpen(!isDetailOpen)}
                            style={{
                                background: 'none',
                                border: 'none',
                                padding: 0,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.75rem',
                                color: 'var(--muted-foreground)',
                                fontWeight: '600'
                            }}
                        >
                            {isDetailOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            상세 설명
                        </button>
                        {isDetailOpen && (
                            <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--muted-foreground)', lineHeight: '1.5' }}>{detailContent}</p>
                        )}
                    </div>
                )}

                {msg.source && (
                    <div className="source-container" style={{ marginTop: '0.5rem', borderTop: '1px solid rgba(0,0,0,0.1)', paddingTop: '0.5rem' }}>
                        <button
                            onClick={() => setIsSourceOpen(!isSourceOpen)}
                            style={{
                                background: 'none',
                                border: 'none',
                                padding: 0,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontSize: '0.75rem',
                                color: msg.role === 'user' ? 'rgba(255,255,255,0.9)' : 'var(--muted-foreground)',
                                fontWeight: '600'
                            }}
                        >
                            {isSourceOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            출처
                        </button>

                        {isSourceOpen && (
                            <div style={{
                                fontSize: '0.75rem',
                                color: msg.role === 'user' ? 'rgba(255,255,255,0.85)' : '#6C757D',
                                marginTop: '0.5rem',
                                fontStyle: 'italic',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '4px',
                                animation: 'fadeIn 0.2s ease-in-out'
                            }}>
                                <div>
                                    <strong>출처:</strong> {msg.source.filename}
                                    {msg.source.scene_index !== undefined && ` (Scene ${msg.source.scene_index + 1})`}
                                    {` (유사도: ${(msg.similarity! * 100).toFixed(1)}%)`}
                                </div>
                                {msg.source.summary && (
                                    <div style={{
                                        backgroundColor: msg.role === 'user' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.03)',
                                        padding: '6px',
                                        borderRadius: '4px',
                                        marginTop: '2px',
                                        borderLeft: '2px solid var(--primary)',
                                        fontSize: '0.8rem',
                                        lineHeight: '1.4'
                                    }}>
                                        {msg.source.summary}
                                    </div>
                                )}
                                {msg.source.scene_index !== undefined && onNavigateToScene && (
                                    <button
                                        onClick={() => {
                                            onNavigateToScene(msg.source!.scene_index!);
                                        }}
                                        disabled={!!(msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId)}
                                        style={{
                                            background: msg.role === 'user' ? 'rgba(255,255,255,0.2)' : 'var(--primary)',
                                            border: msg.role === 'user' ? '1px solid rgba(255,255,255,0.3)' : 'none',
                                            borderRadius: '4px',
                                            color: 'white',
                                            padding: '4px 8px',
                                            cursor: (msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId) ? 'not-allowed' : 'pointer',
                                            opacity: (msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId) ? 0.5 : 1,
                                            alignSelf: 'flex-start',
                                            fontSize: '0.75rem',
                                            marginTop: '6px',
                                            transition: 'all 0.2s'
                                        }}
                                        title={msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId ? '다른 회차의 장면입니다.' : ''}
                                    >
                                        → {msg.source.chapter_id ? `Ch.${msg.source.chapter_id} ` : ''}Scene {msg.source.scene_index + 1}로 이동
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

interface ChatInterfaceProps {
    onNavigateToScene?: (sceneIndex: number) => void;
    novelId?: number;
    chapterId?: number;
}

export function ChatInterface({ onNavigateToScene, novelId, chapterId }: ChatInterfaceProps) {
    const [message, setMessage] = useState('');
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: '안녕하세요! 소설에 대해 무엇이든 물어보세요.'
        }
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        if (!message.trim() || isLoading) return;

        const userMessage = message.trim();
        setMessage('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        // 스트리밍 플레이스홀더 추가
        setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }]);

        let metaInfo: StreamMeta | null = null;

        try {
            await askQuestionStream(
                { question: userMessage, novel_id: novelId, chapter_id: chapterId, alpha: 0.32, similarity_threshold: 0.35 },
                // onToken: 마지막 메시지에 토큰 누적
                (token) => {
                    setMessages(prev => {
                        const arr = [...prev];
                        const last = arr[arr.length - 1];
                        arr[arr.length - 1] = { ...last, content: last.content + token };
                        return arr;
                    });
                },
                // onMeta: 출처/유사도 정보 저장
                (meta) => { metaInfo = meta; },
                // onDone: 스트리밍 완료 → isStreaming 해제 + 메타 반영
                () => {
                    setMessages(prev => {
                        const arr = [...prev];
                        const last = arr[arr.length - 1];
                        arr[arr.length - 1] = {
                            ...last,
                            isStreaming: false,
                            source: metaInfo?.source ?? null,
                            similarity: metaInfo?.similarity ?? 0
                        };
                        return arr;
                    });
                }
            );
        } catch (err: any) {
            console.error('Chat error:', err);
            setMessages(prev => {
                const arr = [...prev];
                arr[arr.length - 1] = { role: 'assistant', content: `오류: ${err.message || '답변 생성 중 오류가 발생했습니다.'}` };
                return arr;
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chatbot-container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="chatbot-messages" style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
                {messages.map((msg, idx) => (
                    msg.isStreaming && !msg.content ? null : <ChatMessageItem key={idx} msg={msg} onNavigateToScene={onNavigateToScene} chapterId={chapterId} />
                ))}
                {isLoading && messages[messages.length - 1]?.content === '' && (
                    <div className="chatbot-message assistant" style={{ alignSelf: 'flex-start' }}>
                        <div className="chatbot-message-bubble assistant-bubble" style={{ padding: '0.75rem 1rem', borderRadius: '1.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Loader2 size={16} className="animate-spin" />
                                <span>답변 생성 중...</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <div className="chatbot-input-area" style={{ padding: '1rem', display: 'flex', gap: '0.5rem' }}>
                <input
                    type="text"
                    className="chatbot-input"
                    placeholder="메시지를 입력하세요..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={isLoading}
                    style={{ flex: 1, padding: '0.75rem', borderRadius: '0.5rem', fontSize: '0.95rem', outline: 'none', transition: 'border-color 0.2s' }}
                />
                <button
                    className="chatbot-send"
                    onClick={handleSend}
                    disabled={isLoading || !message.trim()}
                    style={{ background: 'var(--primary)', color: 'var(--primary-foreground)', border: 'none', borderRadius: '0.5rem', padding: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'transform 0.2s', minWidth: '45px' }}
                >
                    {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                </button>
            </div>
        </div>
    );
}

export function ChatBot({ novelId, chapterId, onNavigateToScene }: { novelId?: number, chapterId?: number, onNavigateToScene?: (idx: number) => void }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            {/* Chatbot Panel */}
            {isOpen && (
                <div className="chatbot-panel" style={{
                    position: 'fixed',
                    bottom: '85px',
                    right: '25px',
                    width: '380px',
                    height: '500px',
                    borderRadius: '1rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 1000
                }}>
                    <div className="chatbot-header" style={{
                        padding: '1rem',
                        background: 'var(--modal-header-bg)',
                        color: 'var(--modal-header-text)',
                        borderTopLeftRadius: '1rem',
                        borderTopRightRadius: '1rem',
                        borderBottom: 'none',
                        display: 'flex',
                        justifyContent: 'flex-end',
                        alignItems: 'center',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
                    }}>
                        <button className="chatbot-close" onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--modal-header-text)', transition: 'opacity 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'} onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}>
                            <X size={20} />
                        </button>
                    </div>
                    <ChatInterface onNavigateToScene={onNavigateToScene} novelId={novelId} chapterId={chapterId} />
                </div>
            )}

            {/* Chatbot Toggle Button */}
            <button
                className="chatbot-toggle-btn"
                onClick={() => setIsOpen(!isOpen)}
                title="AI 어시스턴트"
                style={{
                    position: 'fixed',
                    bottom: '20px',
                    right: '20px',
                    width: '50px',
                    height: '50px',
                    borderRadius: '50%',
                    background: 'var(--primary)',
                    color: 'var(--primary-foreground)',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}
            >
                {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
            </button>
        </>
    );
}


