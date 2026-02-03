import { MessageCircle, X, Send, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { askQuestion, ChatAnswerResponse } from '../api/chat';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    source?: {
        filename: string;
        scene_index?: number;
        total_scenes: number;
    } | null;
    similarity?: number;
}



function ChatMessageItem({ msg, onNavigateToScene }: { msg: Message, onNavigateToScene?: (idx: number) => void }) {
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
            <div style={{
                background: msg.role === 'user' ? 'white' : '#f1f3f5',
                color: 'black',
                padding: '0.75rem 1rem',
                borderRadius: '1.5rem',
                maxWidth: '100%',
                border: msg.role === 'user' ? '1px solid #333' : 'none'
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
                                color: '#666',
                                fontWeight: 'bold'
                            }}
                        >
                            {isDetailOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            상세 설명
                        </button>
                        {isDetailOpen && (
                            <p style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem', fontSize: '0.9rem', color: '#333' }}>{detailContent}</p>
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
                                color: msg.role === 'user' ? '#666' : '#666',
                                fontWeight: 'bold'
                            }}
                        >
                            {isSourceOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            출처
                        </button>

                        {isSourceOpen && (
                            <div style={{
                                fontSize: '0.75rem',
                                color: msg.role === 'user' ? '#666' : '#888',
                                marginTop: '0.5rem',
                                fontStyle: 'italic',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '4px',
                                animation: 'fadeIn 0.2s ease-in-out'
                            }}>
                                <div>출처: {msg.source.filename} (유사도: {(msg.similarity! * 100).toFixed(1)}%)</div>
                                {msg.source.scene_index !== undefined && onNavigateToScene && (
                                    <button
                                        onClick={() => onNavigateToScene(msg.source!.scene_index!)}
                                        style={{
                                            background: '#4F46E5',
                                            border: 'none',
                                            borderRadius: '4px',
                                            color: 'white',
                                            padding: '4px 8px',
                                            cursor: 'pointer',
                                            alignSelf: 'flex-start',
                                            fontSize: '0.75rem',
                                            marginTop: '2px'
                                        }}
                                    >
                                        → Scene {msg.source.scene_index + 1}로 이동
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
}

export function ChatInterface({ onNavigateToScene }: ChatInterfaceProps) {
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
        if (message.trim() && !isLoading) {
            const userMessage = message.trim();
            setMessage('');
            // Add user message to chat
            setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
            setIsLoading(true);

            try {
                // Call API
                const response: ChatAnswerResponse = await askQuestion({
                    question: userMessage,
                    alpha: 0.32,
                    similarity_threshold: 0.0
                });

                // Add assistant response to chat
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: response.answer,
                    source: response.source,
                    similarity: response.similarity
                }]);
            } catch (err: any) {
                console.error('Chat error:', err);
                const errorMessage = err.response?.data?.detail || err.message || '답변 생성 중 오류가 발생했습니다.';
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `오류: ${errorMessage}`
                }]);
            } finally {
                setIsLoading(false);
            }
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
                    <ChatMessageItem key={idx} msg={msg} onNavigateToScene={onNavigateToScene} />
                ))}
                {isLoading && (
                    <div className="chatbot-message assistant" style={{ alignSelf: 'flex-start' }}>
                        <div style={{ background: '#f1f3f5', padding: '0.75rem', borderRadius: '1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Loader2 size={16} className="animate-spin" />
                                <span>답변 생성 중...</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
            <div className="chatbot-input-area" style={{ padding: '1rem', borderTop: '1px solid #eee', display: 'flex', gap: '0.5rem' }}>
                <input
                    type="text"
                    className="chatbot-input"
                    placeholder="메시지를 입력하세요..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={isLoading}
                    style={{ flex: 1, padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid #ddd' }}
                />
                <button
                    className="chatbot-send"
                    onClick={handleSend}
                    disabled={isLoading || !message.trim()}
                    style={{ background: '#007bff', color: 'white', border: 'none', borderRadius: '0.5rem', padding: '0.5rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                    {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                </button>
            </div>
        </div>
    );
}

export function ChatBot() {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <>
            {/* Chatbot Panel */}
            {isOpen && (
                <div className="chatbot-panel" style={{
                    position: 'fixed',
                    bottom: '80px',
                    right: '20px',
                    width: '350px',
                    height: '500px',
                    background: 'white',
                    borderRadius: '1rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 1000
                }}>
                    <div className="chatbot-header" style={{
                        padding: '1rem',
                        background: '#f8f9fa',
                        color: '#212529',
                        borderTopLeftRadius: '1rem',
                        borderTopRightRadius: '1rem',
                        borderBottom: '1px solid #dee2e6',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                    }}>
                        <div className="chatbot-header-content" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <MessageCircle size={20} />
                            <h3 className="chatbot-title" style={{ margin: 0 }}>AI 어시스턴트</h3>
                        </div>
                        <button className="chatbot-close" onClick={() => setIsOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#212529' }}>
                            <X size={20} />
                        </button>
                    </div>
                    <ChatInterface />
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
                    height: '500px',
                    borderRadius: '50%',
                    background: '#007bff',
                    color: 'white',
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


