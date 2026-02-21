import { useState, useEffect, useRef } from 'react';
import { X, Loader, Sparkles, Send, Bot, User, Trash2 } from 'lucide-react';

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
}

interface PredictionSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    messages: Message[];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
    onClearChat?: () => void;
}

export function PredictionSidebar({ isOpen, onClose, messages, onSendMessage, isLoading, onClearChat }: PredictionSidebarProps) {
    const [inputValue, setInputValue] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Helper to format assistant messages: Add double line break every 2 sentences
    const formatMessage = (content: string) => {
        const sentences = content.match(/[^.!?]+[.!?]+(\s|$)/g);

        if (!sentences) return content;

        let formatted = "";
        for (let i = 0; i < sentences.length; i++) {
            formatted += sentences[i];
            if ((i + 1) % 2 === 0 && i < sentences.length - 1) {
                formatted += "\n\n";
            }
        }
        return formatted || content;
    };

    useEffect(() => {
        if (isOpen) {
            scrollToBottom();
        }
    }, [messages, isOpen, isLoading]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const handleSubmit = () => {
        if (!inputValue.trim() || isLoading) return;
        onSendMessage(inputValue);
        setInputValue("");
    };

    if (!isOpen) return null;

    return (
        <div
            style={{
                position: 'fixed',
                bottom: '16px',
                right: '20px',
                width: '500px',
                height: '850px',
                backgroundColor: 'var(--modal-bg)',
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
            <div style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--modal-border)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: 'var(--modal-header-bg)',
                color: 'var(--modal-header-text)',
                borderRadius: '16px 16px 0 0'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sparkles size={20} strokeWidth={2.5} className={isLoading ? 'animate-spin' : ''} style={{ color: 'var(--primary)' }} />
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 'bold', color: 'inherit' }}>스토리 예측 챗봇</h3>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                    {onClearChat && messages.length > 0 && (
                        <button
                            onClick={onClearChat}
                            title="대화 지우기"
                            style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                color: 'var(--muted-foreground)',
                                padding: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                            }}
                        >
                            <Trash2 size={18} strokeWidth={2.5} />
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: 'var(--muted-foreground)',
                            padding: '4px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <X size={20} strokeWidth={2.5} />
                    </button>
                </div>
            </div>

            {/* Chat Content */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '20px',
                backgroundColor: 'var(--modal-bg)',
                display: 'flex',
                flexDirection: 'column',
                gap: '20px'
            }}>
                {messages.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        color: 'var(--muted-foreground)',
                        marginTop: '60px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px'
                    }}>
                        <Sparkles size={48} strokeWidth={2.5} style={{ opacity: 0.2, color: 'var(--primary)' }} />
                        <p style={{ lineHeight: '1.5' }}>
                            "다음 전개는 어떻게 될까?"<br />
                            AI와 함께 이야기를 만들어보세요.
                        </p>
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} style={{
                        display: 'flex',
                        justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        gap: '12px'
                    }}>
                        {msg.role === 'assistant' && (
                            <div style={{
                                width: '32px', height: '32px',
                                borderRadius: '50%',
                                backgroundColor: 'var(--secondary)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                flexShrink: 0,
                                marginTop: '4px'
                            }}>
                                <Bot size={18} strokeWidth={2.5} style={{ color: 'var(--primary)' }} />
                            </div>
                        )}

                        <div style={{
                            maxWidth: '85%',
                            padding: '12px 16px',
                            borderRadius: '12px',
                            borderTopLeftRadius: msg.role === 'assistant' ? '2px' : '12px',
                            borderTopRightRadius: msg.role === 'user' ? '2px' : '12px',
                            backgroundColor: msg.role === 'user' ? 'var(--primary)' : 'var(--input-bg)',
                            color: msg.role === 'user' ? 'var(--primary-foreground)' : 'var(--input-text)',
                            boxShadow: msg.role === 'assistant' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                            border: msg.role === 'assistant' ? '1px solid var(--input-border)' : 'none',
                            lineHeight: '1.6',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word'
                        }}>
                            {msg.role === 'assistant' ? formatMessage(msg.content) : msg.content}
                        </div>

                        {msg.role === 'user' && (
                            <div style={{
                                width: '32px', height: '32px',
                                borderRadius: '50%',
                                backgroundColor: 'var(--secondary)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                flexShrink: 0,
                                marginTop: '4px'
                            }}>
                                <User size={18} strokeWidth={2.5} style={{ color: 'var(--muted-foreground)' }} />
                            </div>
                        )}
                    </div>
                ))}

                {isLoading && (
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <div style={{
                            width: '32px', height: '32px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--secondary)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            flexShrink: 0
                        }}>
                            <Loader className="animate-spin" size={18} strokeWidth={2.5} style={{ color: 'var(--primary)' }} />
                        </div>
                        <div style={{
                            padding: '12px 16px',
                            borderRadius: '12px',
                            borderTopLeftRadius: '2px',
                            backgroundColor: 'var(--input-bg)',
                            border: '1px solid var(--input-border)',
                            color: 'var(--muted-foreground)',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                        }}>
                            이야기를 생성하고 있습니다...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{
                padding: '16px',
                backgroundColor: 'var(--modal-bg)',
                borderTop: '1px solid var(--modal-border)',
                borderRadius: '0 0 16px 16px'
            }}>
                <div style={{
                    display: 'flex',
                    gap: '10px',
                    alignItems: 'flex-end',
                    backgroundColor: 'var(--input-bg)',
                    padding: '8px',
                    borderRadius: '12px',
                    border: '1px solid var(--input-border)'
                }}>
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="메시지를 입력하세요..."
                        style={{
                            flex: 1,
                            border: 'none',
                            background: 'transparent',
                            resize: 'none',
                            height: 'auto',
                            minHeight: '24px',
                            maxHeight: '120px',
                            padding: '8px',
                            fontSize: '0.95rem',
                            outline: 'none',
                            fontFamily: 'inherit',
                            overflowY: 'auto',
                            color: 'var(--input-text)'
                        }}
                        rows={1}
                        onInput={(e) => {
                            e.currentTarget.style.height = 'auto';
                            e.currentTarget.style.height = (e.currentTarget.scrollHeight) + 'px';
                        }}
                    />
                    <button
                        onClick={handleSubmit}
                        disabled={!inputValue.trim() || isLoading}
                        style={{
                            backgroundColor: inputValue.trim() && !isLoading ? 'var(--primary)' : 'var(--muted)',
                            color: inputValue.trim() && !isLoading ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
                            border: 'none',
                            borderRadius: '8px',
                            padding: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: inputValue.trim() && !isLoading ? 'pointer' : 'not-allowed',
                            transition: 'background-color 0.2s',
                            width: '36px',
                            height: '36px'
                        }}
                    >
                        {isLoading ? <Loader size={18} strokeWidth={2.5} className="animate-spin" /> : <Send size={18} strokeWidth={2.5} />}
                    </button>
                </div>
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
                .animate-spin {
                    animation: spin 1s linear infinite;
                }
            `}</style>
        </div>
    );
}
