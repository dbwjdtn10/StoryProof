import { MessageCircle, X, Send, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import { askQuestionStream, StreamMeta } from '../api/chat';
import '../chatbot.css';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    source?: {
        filename: string;
        scene_index?: number;
        chapter_id?: number;
        summary?: string;
        total_scenes: number;
    } | null;
    similarity?: number;
}

/** Strip markdown bold markers and split into main/detail sections */
function parseAssistantContent(content: string): { main: string; detail: string } {
    // Match both **핵심 요약** / **상세 설명** and [핵심 요약] / [상세 설명] formats
    const detailSplit = content.split(/\*{0,2}\[?상세 설명\]?\*{0,2}/);
    let main = detailSplit[0];
    const detail = detailSplit[1]?.trim() || '';

    // Remove "핵심 요약" header
    main = main.replace(/\*{0,2}\[?핵심 요약\]?\*{0,2}/, '').trim();
    // Strip remaining markdown bold
    main = main.replace(/\*\*(.*?)\*\*/g, '$1');

    return { main, detail: detail.replace(/\*\*(.*?)\*\*/g, '$1') };
}


function ChatMessageItem({ msg, onNavigateToScene, chapterId }: { msg: Message, onNavigateToScene?: (idx: number) => void, chapterId?: number }) {
    const [isSourceOpen, setIsSourceOpen] = useState(false);
    const [isDetailOpen, setIsDetailOpen] = useState(false);

    const { main: mainContent, detail: detailContent } = msg.role === 'assistant'
        ? parseAssistantContent(msg.content)
        : { main: msg.content, detail: '' };

    return (
        <div className={`chatbot-message ${msg.role}`} style={{ marginBottom: '1rem', alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div className={`chatbot-message-bubble ${msg.role === 'user' ? 'user-bubble' : 'assistant-bubble'}`} style={{
                padding: '0.75rem 1rem',
                borderRadius: '1.5rem',
                maxWidth: '100%',
                backgroundColor: msg.role === 'user' ? 'var(--primary)' : 'var(--chat-assistant-bg)',
                color: msg.role === 'user' ? 'var(--primary-foreground)' : 'var(--chat-assistant-text)',
                border: msg.role === 'assistant' ? '1px solid var(--border)' : 'none',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
            }}>
                <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{mainContent}</p>

                {detailContent && (
                    <div className="detail-container" style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border)', paddingTop: '0.5rem' }}>
                        <button
                            onClick={() => setIsDetailOpen(!isDetailOpen)}
                            style={{
                                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                                display: 'flex', alignItems: 'center', gap: '4px',
                                fontSize: '0.75rem', color: 'var(--muted-foreground)', fontWeight: '600'
                            }}
                        >
                            {isDetailOpen ? <ChevronUp size={14} strokeWidth={2.5} /> : <ChevronDown size={14} strokeWidth={2.5} />}
                            상세 설명
                        </button>
                        {isDetailOpen && (
                            <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--muted-foreground)', lineHeight: '1.5' }}>{detailContent}</p>
                        )}
                    </div>
                )}

                {msg.source && (
                    <div className="source-container" style={{ marginTop: '0.5rem', borderTop: '1px solid var(--border)', paddingTop: '0.5rem' }}>
                        <button
                            onClick={() => setIsSourceOpen(!isSourceOpen)}
                            style={{
                                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                                display: 'flex', alignItems: 'center', gap: '4px',
                                fontSize: '0.75rem',
                                color: msg.role === 'user' ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
                                opacity: 0.9, fontWeight: '600'
                            }}
                        >
                            {isSourceOpen ? <ChevronUp size={14} strokeWidth={2.5} /> : <ChevronDown size={14} strokeWidth={2.5} />}
                            출처
                        </button>

                        {isSourceOpen && (
                            <div style={{
                                fontSize: '0.75rem',
                                color: msg.role === 'user' ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
                                opacity: 0.85, marginTop: '0.5rem', fontStyle: 'italic',
                                display: 'flex', flexDirection: 'column', gap: '4px',
                                animation: 'fadeIn 0.2s ease-in-out'
                            }}>
                                <div>
                                    <strong>출처:</strong> {msg.source.filename}
                                    {msg.source.scene_index !== undefined && ` (Scene ${msg.source.scene_index + 1})`}
                                </div>
                                {msg.source.summary && (
                                    <div style={{
                                        backgroundColor: 'rgba(0,0,0,0.1)', padding: '6px', borderRadius: '4px',
                                        marginTop: '2px', borderLeft: '2px solid currentColor',
                                        fontSize: '0.8rem', lineHeight: '1.4'
                                    }}>
                                        {msg.source.summary}
                                    </div>
                                )}
                                {msg.source.scene_index !== undefined && onNavigateToScene && (
                                    <button
                                        onClick={() => onNavigateToScene(msg.source!.scene_index!)}
                                        disabled={!!(msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId)}
                                        style={{
                                            background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.3)',
                                            borderRadius: '4px', color: 'currentColor', padding: '4px 8px',
                                            cursor: (msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId) ? 'not-allowed' : 'pointer',
                                            opacity: (msg.source.chapter_id && chapterId && msg.source.chapter_id !== chapterId) ? 0.5 : 1,
                                            alignSelf: 'flex-start', fontSize: '0.75rem', marginTop: '6px', transition: 'all 0.2s'
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
        { role: 'assistant', content: '안녕하세요! 소설에 대해 무엇이든 물어보세요.' }
    ]);
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortRef = useRef(false);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = useCallback(async () => {
        if (!message.trim() || isLoading) return;
        const userMessage = message.trim();
        setMessage('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);
        abortRef.current = false;

        // Add placeholder assistant message for streaming
        const assistantIdx = messages.length + 1; // +1 for the user message we just added
        setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

        try {
            await askQuestionStream(
                {
                    question: userMessage,
                    novel_id: novelId,
                    chapter_id: chapterId,
                },
                // onToken
                (text: string) => {
                    if (abortRef.current) return;
                    setMessages(prev => {
                        const updated = [...prev];
                        const target = updated[assistantIdx];
                        if (target) target.content += text;
                        return updated;
                    });
                },
                // onMeta
                (meta: StreamMeta) => {
                    setMessages(prev => {
                        const updated = [...prev];
                        const target = updated[assistantIdx];
                        if (target) {
                            target.source = meta.source;
                            target.similarity = meta.similarity;
                        }
                        return updated;
                    });
                    if (!meta.found_context) {
                        setMessages(prev => {
                            const updated = [...prev];
                            const target = updated[assistantIdx];
                            if (target) target.content = '죄송합니다. 관련 내용을 찾을 수 없습니다.';
                            return updated;
                        });
                    }
                },
                // onDone
                () => { setIsLoading(false); }
            );
        } catch (err: any) {
            console.error('Chat stream error:', err);
            setMessages(prev => {
                const updated = [...prev];
                const target = updated[assistantIdx];
                if (target) target.content = `오류: ${err.message || '답변 생성 중 오류가 발생했습니다.'}`;
                return updated;
            });
            setIsLoading(false);
        }
    }, [message, isLoading, messages.length, novelId, chapterId]);

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chatbot-container" style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'var(--modal-bg)' }}>
            <div className="chatbot-messages" style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
                {messages.map((msg, idx) => {
                    if (msg.role === 'assistant' && !msg.content && isLoading) return null;
                    return <ChatMessageItem key={idx} msg={msg} onNavigateToScene={onNavigateToScene} chapterId={chapterId} />;
                })}
                {isLoading && messages[messages.length - 1]?.content === '' && (
                    <div className="chatbot-message assistant" style={{ alignSelf: 'flex-start' }}>
                        <div className="chatbot-message-bubble assistant-bubble" style={{
                            padding: '0.75rem 1rem', borderRadius: '1.5rem',
                            backgroundColor: 'var(--chat-assistant-bg)',
                            border: '1px solid var(--border)', color: 'var(--chat-assistant-text)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Loader2 size={16} strokeWidth={2.5} className="animate-spin" style={{ color: 'var(--muted-foreground)' }} />
                                <span style={{ color: 'var(--muted-foreground)' }}>답변 생성 중...</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <div className="chatbot-input-area" style={{
                padding: '1rem', display: 'flex', gap: '0.5rem',
                backgroundColor: 'var(--modal-bg)', borderTop: '1px solid var(--border)'
            }}>
                <input
                    type="text" className="chatbot-input"
                    placeholder="메시지를 입력하세요..."
                    value={message} maxLength={500}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyPress}
                    disabled={isLoading}
                    style={{
                        flex: 1, padding: '0.75rem', borderRadius: '0.5rem', fontSize: '0.95rem',
                        outline: 'none', transition: 'border-color 0.2s',
                        backgroundColor: 'var(--input-bg)', color: 'var(--input-text)',
                        border: '1px solid var(--input-border)'
                    }}
                />
                <button
                    className="chatbot-send" onClick={handleSend}
                    disabled={isLoading || !message.trim()}
                    style={{
                        backgroundColor: 'var(--primary)', color: 'var(--primary-foreground)',
                        border: 'none', borderRadius: '0.5rem', padding: '0.75rem',
                        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'transform 0.2s', minWidth: '45px',
                        opacity: isLoading || !message.trim() ? 0.5 : 1
                    }}
                >
                    {isLoading ? <Loader2 size={20} strokeWidth={2.5} className="animate-spin" /> : <Send size={20} strokeWidth={2.5} />}
                </button>
            </div>
        </div>
    );
}

export function ChatBot({ novelId, chapterId, onNavigateToScene }: { novelId?: number, chapterId?: number, onNavigateToScene?: (idx: number) => void }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            {isOpen && (
                <div className="chatbot-panel" style={{
                    position: 'fixed', bottom: '85px', right: '25px', width: '380px', height: '500px',
                    borderRadius: '1rem', boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    display: 'flex', flexDirection: 'column', zIndex: 1000,
                    backgroundColor: 'var(--modal-bg)', border: '1px solid var(--modal-border)'
                }}>
                    <div className="chatbot-header" style={{
                        padding: '1rem', backgroundColor: 'var(--modal-header-bg)',
                        color: 'var(--modal-header-text)',
                        borderTopLeftRadius: '1rem', borderTopRightRadius: '1rem',
                        borderBottom: '1px solid var(--border)',
                        display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                    }}>
                        <button className="chatbot-close" onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'currentColor', transition: 'opacity 0.2s' }} onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'} onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}>
                            <X size={20} strokeWidth={2.5} />
                        </button>
                    </div>
                    <ChatInterface onNavigateToScene={onNavigateToScene} novelId={novelId} chapterId={chapterId} />
                </div>
            )}

            <button
                className="chatbot-toggle-btn" onClick={() => setIsOpen(!isOpen)}
                title="AI 어시스턴트"
                style={{
                    position: 'fixed', bottom: '20px', right: '20px', width: '50px', height: '50px',
                    borderRadius: '50%', backgroundColor: 'var(--primary)',
                    color: 'var(--primary-foreground)', border: 'none',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.2)', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }}
            >
                {isOpen ? <X size={24} strokeWidth={2.5} /> : <MessageCircle size={24} strokeWidth={2.5} />}
            </button>
        </>
    );
}
