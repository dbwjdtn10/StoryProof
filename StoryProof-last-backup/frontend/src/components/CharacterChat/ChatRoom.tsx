import React, { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';
import { getMessages, sendMessage, CharacterChatRoom, CharacterChatMessage } from '../../api/characterChat';

interface ChatRoomProps {
    room: CharacterChatRoom;
}

export function ChatRoom({ room }: ChatRoomProps) {
    const [messages, setMessages] = useState<CharacterChatMessage[]>([]);
    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchHistory = async () => {
        try {
            const data = await getMessages(room.id);
            setMessages(data);
            scrollToBottom();
        } catch (error) {
            console.error("Failed to fetch messages:", error);
        }
    };

    useEffect(() => {
        fetchHistory();
        // Poll for updates or real-time could be added here
    }, [room.id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!inputText.trim() || loading) return;

        const text = inputText;
        setInputText(''); // Optimistic clear
        setLoading(true);

        // Optimistic UI update
        const tempMsg: CharacterChatMessage = {
            id: Date.now(), // Temp ID
            room_id: room.id,
            role: 'user',
            content: text,
            created_at: new Date().toISOString()
        };
        setMessages(prev => [...prev, tempMsg]);

        try {
            const newMessages = await sendMessage(room.id, text);
            // Replace with actual messages from server (which includes assistant response)
            // But we need to keep history + new ones. 
            // The API returns [user_msg, ai_msg] usually.
            // Or getMessages returns all.
            // Let's assume sendMessage returns the newly created messages.

            // To be safe and consistent, let's refresh history or append if we trust API return.
            // My backend implementation returns [user_msg, ai_msg].

            // Filter out temp message if we re-fetch, but appending is smoother.
            // Let's remove the optimistic one and add the real ones.
            setMessages(prev => {
                const filtered = prev.filter(m => m.id !== tempMsg.id);
                return [...filtered, ...newMessages];
            });
        } catch (error) {
            console.error("Failed to send message:", error);
            // Revert optimistic update
            setMessages(prev => prev.filter(m => m.id !== tempMsg.id));
            alert("메시지 전송 실패");
            setInputText(text); // Restore text
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#b2c7da' }}>
            {/* Chat Area */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ textAlign: 'center', fontSize: '0.8rem', color: '#fff', marginBottom: '10px', opacity: 0.8 }}>
                    {new Date().toLocaleDateString()}
                </div>

                {messages.map((msg, index) => {
                    const isUser = msg.role === 'user';
                    return (
                        <div
                            key={msg.id || index}
                            style={{
                                display: 'flex',
                                justifyContent: isUser ? 'flex-end' : 'flex-start',
                                alignItems: 'flex-start',
                                gap: '8px'
                            }}
                        >
                            {!isUser && (
                                <div style={{
                                    width: '36px', height: '36px', borderRadius: '14px',
                                    backgroundColor: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '0.8rem', fontWeight: 'bold'
                                }}>
                                    {room.character_name.charAt(0)}
                                </div>
                            )}

                            <div style={{ maxWidth: '70%' }}>
                                {!isUser && (
                                    <div style={{ fontSize: '0.8rem', marginBottom: '4px', color: '#555' }}>
                                        {room.character_name}
                                    </div>
                                )}
                                <div style={{
                                    backgroundColor: isUser ? '#fee500' : '#ffffff',
                                    padding: '8px 12px',
                                    borderRadius: isUser ? '12px 0 12px 12px' : '0 12px 12px 12px',
                                    fontSize: '0.95rem',
                                    lineHeight: '1.4',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word'
                                }}>
                                    {msg.content}
                                </div>
                                <div style={{
                                    fontSize: '0.7rem',
                                    color: '#555',
                                    marginTop: '2px',
                                    textAlign: isUser ? 'right' : 'left'
                                }}>
                                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>
                        </div>
                    );
                })}
                {loading && (
                    <div style={{ display: 'flex', justifyContent: 'flex-start', paddingLeft: '44px' }}>
                        <div style={{ backgroundColor: 'white', padding: '8px 12px', borderRadius: '12px', fontSize: '0.8rem', color: '#999' }}>
                            ...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{ backgroundColor: 'white', padding: '10px', display: 'flex', gap: '8px' }}>
                <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="메시지를 입력하세요..."
                    style={{
                        flex: 1,
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        padding: '8px',
                        resize: 'none',
                        height: '40px',
                        fontFamily: 'inherit'
                    }}
                />
                <button
                    onClick={handleSend}
                    disabled={loading || !inputText.trim()}
                    style={{
                        backgroundColor: '#fee500',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        width: '50px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: loading ? '#999' : '#3b1e1e'
                    }}
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    );
}
