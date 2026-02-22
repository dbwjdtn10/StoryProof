
import { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { X, Sparkles, Send, Loader, User, Bot } from 'lucide-react';

interface PredictionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (scenario: string) => Promise<string | null>;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
}

export function PredictionModal({ isOpen, onClose, onSubmit }: PredictionModalProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputValue, setInputValue] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    if (!isOpen) return null;

    const handleSubmit = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: inputValue
        };

        setMessages(prev => [...prev, userMsg]);
        setInputValue("");
        setIsLoading(true);

        try {
            const result = await onSubmit(userMsg.content);

            if (result) {
                const botMsg: Message = {
                    id: (Date.now() + 1).toString(),
                    role: 'assistant',
                    content: result
                };
                setMessages(prev => [...prev, botMsg]);
            }
        } catch (error) {
            console.error("Prediction failed", error);
            toast.error("예측 분석에 실패했습니다. 다시 시도해주세요.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 1100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        }}>
            <div style={{
                backgroundColor: 'white',
                width: '600px',
                maxWidth: '90%',
                height: '80vh',
                borderRadius: '16px',
                boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden'
            }}>
                {/* Header */}
                <div style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid #eee',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    backgroundColor: '#fff'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{
                            backgroundColor: 'rgba(124, 58, 237, 0.1)',
                            padding: '8px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <Sparkles size={20} color="#7C3AED" />
                        </div>
                        <div>
                            <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 'bold' }}>스토리 예측 챗봇</h2>
                            <p style={{ margin: 0, fontSize: '0.8rem', color: '#6b7280' }}>가설을 세우고 이야기를 나누어보세요</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: '4px' }}
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Chat Area */}
                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '20px',
                    backgroundColor: '#f9fafb',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '20px'
                }}>
                    {messages.length === 0 && (
                        <div style={{
                            textAlign: 'center',
                            color: '#9ca3af',
                            marginTop: '40px',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            gap: '12px'
                        }}>
                            <Sparkles size={48} style={{ opacity: 0.2 }} />
                            <p>"만약 앨리스가 토끼를 따라가지 않았다면?"<br />상상력을 발휘해 질문해보세요.</p>
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
                                    backgroundColor: '#EDE9FE',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    flexShrink: 0
                                }}>
                                    <Bot size={18} color="#7C3AED" />
                                </div>
                            )}

                            <div style={{
                                maxWidth: '80%',
                                padding: '12px 16px',
                                borderRadius: '12px',
                                borderTopLeftRadius: msg.role === 'assistant' ? '0' : '12px',
                                borderTopRightRadius: msg.role === 'user' ? '0' : '12px',
                                backgroundColor: msg.role === 'user' ? '#7C3AED' : 'white',
                                color: msg.role === 'user' ? 'white' : '#1f2937',
                                boxShadow: msg.role === 'assistant' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                                border: msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
                                lineHeight: '1.6',
                                whiteSpace: 'pre-wrap'
                            }}>
                                {msg.content}
                            </div>

                            {msg.role === 'user' && (
                                <div style={{
                                    width: '32px', height: '32px',
                                    borderRadius: '50%',
                                    backgroundColor: '#e5e7eb',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    flexShrink: 0
                                }}>
                                    <User size={18} color="#6b7280" />
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <div style={{
                                width: '32px', height: '32px',
                                borderRadius: '50%',
                                backgroundColor: '#EDE9FE',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                flexShrink: 0
                            }}>
                                <Loader className="animate-spin" size={18} color="#7C3AED" />
                            </div>
                            <div style={{
                                padding: '12px 16px',
                                borderRadius: '12px',
                                borderTopLeftRadius: '0',
                                backgroundColor: 'white',
                                border: '1px solid #e5e7eb',
                                color: '#6b7280'
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
                    backgroundColor: 'white',
                    borderTop: '1px solid #eee'
                }}>
                    <div style={{
                        display: 'flex',
                        gap: '10px',
                        alignItems: 'flex-end',
                        backgroundColor: '#f3f4f6',
                        padding: '8px',
                        borderRadius: '12px',
                        border: '1px solid #e5e7eb'
                    }}>
                        <textarea
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="메시지를 입력하세요 (Shift+Enter로 줄바꿈)"
                            style={{
                                flex: 1,
                                border: 'none',
                                background: 'transparent',
                                resize: 'none',
                                height: '24px',
                                maxHeight: '100px',
                                padding: '8px',
                                fontSize: '0.95rem',
                                outline: 'none',
                                fontFamily: 'inherit',
                                overflowY: 'hidden' // Simple auto-grow handling typically needs logic, kept simple for now
                            }}
                            rows={1}
                        />
                        <button
                            onClick={handleSubmit}
                            disabled={!inputValue.trim() || isLoading}
                            style={{
                                backgroundColor: inputValue.trim() && !isLoading ? '#7C3AED' : '#d1d5db',
                                color: 'white',
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
                            {isLoading ? <Loader size={18} className="animate-spin" /> : <Send size={18} />}
                        </button>
                    </div>
                </div>

                <style>{`
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                    .animate-spin {
                        animation: spin 1s linear infinite;
                    }
                `}</style>
            </div>
        </div>
    );
}
