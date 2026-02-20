
import React, { useState, useEffect, useRef } from 'react';
import {
    X, ArrowLeft, MoreVertical, Trash2, SquarePen,
    Plus, Send, Sparkles
} from 'lucide-react';
import { toast } from 'sonner';
import {
    CharacterChatRoom, CharacterChatMessage,
    generatePersona, createRoom, getRooms, sendMessageStream, getMessages, updateRoom, deleteRoom
} from '../api/characterChat';

// ------------------------------------------------------------------
// Components
// ------------------------------------------------------------------

// --- CreateRoomModal ---

interface CreateRoomModalProps {
    novelId: number;
    chapterId?: number;
    onClose: () => void;
    onCreated?: (room: CharacterChatRoom) => void;
    onUpdated?: (room: CharacterChatRoom) => void;
    initialData?: CharacterChatRoom;
    mode?: 'create' | 'edit';
}

function CreateRoomModal({ novelId, chapterId, onClose, onCreated, onUpdated, initialData, mode = 'create' }: CreateRoomModalProps) {
    const [characterName, setCharacterName] = useState(initialData?.character_name || '');
    const [personaPrompt, setPersonaPrompt] = useState(initialData?.persona_prompt || '');
    const [step, setStep] = useState<'input' | 'review'>(mode === 'edit' ? 'review' : 'input');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleGenerate = async () => {
        if (!characterName.trim()) return;
        setLoading(true);
        setError(null);
        try {
            const result = await generatePersona(novelId, characterName, chapterId);
            setPersonaPrompt(result.persona_prompt);
            setStep('review');
        } catch (err: any) {
            setError(err.message || "페르소나 생성 실패");
        } finally {
            setLoading(false);
        }
    };

    const handleCreateOrUpdate = async () => {
        if (!personaPrompt.trim()) return;
        setLoading(true);
        try {
            if (mode === 'create') {
                const room = await createRoom(novelId, characterName, personaPrompt, chapterId);
                onCreated?.(room);
            } else {
                if (initialData?.id) {
                    const room = await updateRoom(initialData.id, personaPrompt);
                    onUpdated?.(room);
                }
            }
        } catch (err: any) {
            setError(err.message || (mode === 'create' ? "대화방 생성 실패" : "대화방 수정 실패"));
            setLoading(false);
        }
    };

    return (
        <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'var(--modal-bg)',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            padding: '20px'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                <h3 style={{ margin: 0, color: 'var(--foreground)' }}>{mode === 'create' ? '새 대화 시작' : '페르소나 수정'}</h3>
                <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--foreground)' }}>
                    <X size={20} />
                </button>
            </div>

            {error && (
                <div style={{
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    color: 'var(--destructive)',
                    padding: '10px',
                    borderRadius: '8px',
                    marginBottom: '10px',
                    fontSize: '0.9rem'
                }}>
                    {error}
                </div>
            )}

            {step === 'input' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: 'var(--foreground)' }}>캐릭터 이름</label>
                        <input
                            type="text"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            placeholder="예: 셜록 홈즈"
                            style={{
                                width: '100%', padding: '12px', borderRadius: '8px',
                                border: '1px solid var(--input-border)',
                                fontSize: '1rem',
                                backgroundColor: 'var(--input-bg)',
                                color: 'var(--input-text)',
                                boxSizing: 'border-box'
                            }}
                        />
                        <p style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)', marginTop: '4px' }}>
                            * 분석된 데이터에 있는 캐릭터 이름을 입력하세요.
                        </p>
                    </div>

                    <button
                        onClick={handleGenerate}
                        disabled={loading || !characterName}
                        style={{
                            backgroundColor: 'var(--modal-header-bg)',
                            color: 'var(--modal-header-text)',
                            border: 'none',
                            padding: '14px',
                            borderRadius: '8px',
                            fontWeight: 'bold',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '8px',
                            opacity: loading ? 0.7 : 1
                        }}
                    >
                        {loading ? '생성 중...' : (
                            <>
                                <Sparkles size={18} />
                                페르소나 생성
                            </>
                        )}
                    </button>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <label style={{ fontWeight: 'bold', color: 'var(--foreground)' }}>페르소나 프롬프트 (수정 가능)</label>
                            <button
                                onClick={handleGenerate}
                                title="AI 자동 업데이트 (현재 분석 데이터 기반)"
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--muted-foreground)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem'
                                }}
                            >
                                <Sparkles size={14} />
                                AI 자동 갱신
                            </button>
                        </div>
                        <textarea
                            value={personaPrompt}
                            onChange={(e) => setPersonaPrompt(e.target.value)}
                            style={{
                                flex: 1,
                                width: '100%',
                                padding: '12px',
                                borderRadius: '8px',
                                border: '1px solid var(--input-border)',
                                fontSize: '0.9rem',
                                resize: 'none',
                                fontFamily: 'monospace',
                                backgroundColor: 'var(--input-bg)',
                                color: 'var(--input-text)'
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                        {mode !== 'edit' && (
                            <button
                                onClick={() => setStep('input')}
                                style={{
                                    flex: 1,
                                    backgroundColor: 'var(--secondary)',
                                    color: 'var(--foreground)',
                                    border: 'none',
                                    padding: '14px',
                                    borderRadius: '8px',
                                    fontWeight: 'bold',
                                    cursor: 'pointer'
                                }}
                            >
                                뒤로
                            </button>
                        )}
                        <button
                            onClick={handleCreateOrUpdate}
                            disabled={loading}
                            style={{
                                flex: 2,
                                backgroundColor: 'var(--modal-header-bg)',
                                color: 'var(--modal-header-text)',
                                border: 'none',
                                padding: '14px',
                                borderRadius: '8px',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                opacity: loading ? 0.7 : 1
                            }}
                        >
                            {loading ? (mode === 'create' ? '생성 중...' : '저장 중...') : (mode === 'create' ? '대화 시작' : '수정 저장')}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

// --- RoomList ---

interface RoomListProps {
    novelId: number;
    chapterId?: number;
    onSelectRoom: (room: CharacterChatRoom) => void;
}

function RoomList({ novelId, chapterId, onSelectRoom }: RoomListProps) {
    const [rooms, setRooms] = useState<CharacterChatRoom[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [roomHover, setRoomHover] = useState<number | null>(null);

    const fetchRooms = async () => {
        try {
            setLoading(true);
            const data = await getRooms(novelId, chapterId);
            setRooms(data);
        } catch (error) {
            console.error("Failed to fetch rooms:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRooms();
    }, [novelId, chapterId]);

    const handleRoomCreated = (newRoom: CharacterChatRoom) => {
        setRooms([newRoom, ...rooms]);
        setIsCreateModalOpen(false);
        onSelectRoom(newRoom);
    };

    return (
        <div style={{ padding: '16px', height: '100%', overflowY: 'auto', backgroundColor: 'var(--modal-bg)' }}>
            {loading ? (
                <div style={{ textAlign: 'center', padding: '20px', color: 'var(--muted-foreground)' }}>로딩 중...</div>
            ) : rooms.length === 0 ? (
                <div style={{ textAlign: 'center', marginTop: '100px', color: 'var(--muted-foreground)' }}>
                    <p>대화방이 없습니다.</p>
                    <p>새로운 캐릭터와 대화를 시작해보세요!</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {rooms.map(room => (
                        <div
                            key={room.id}
                            onClick={() => onSelectRoom(room)}
                            style={{
                                padding: '16px',
                                borderRadius: '12px',
                                backgroundColor: roomHover === room.id ? 'var(--accent)' : 'var(--secondary)',
                                border: '1px solid var(--border)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px',
                                transition: 'background 0.2s'
                            }}
                            onMouseEnter={() => setRoomHover(room.id)}
                            onMouseLeave={() => setRoomHover(null)}
                        >
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '50%',
                                backgroundColor: 'var(--secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <span style={{ fontWeight: 'bold', color: 'var(--muted-foreground)' }}>
                                    {room.character_name.charAt(0)}
                                </span>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 'bold', color: 'var(--foreground)' }}>{room.character_name}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
                                    {new Date(room.updated_at || room.created_at).toLocaleDateString()}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.75rem', color: 'var(--muted-foreground)', paddingBottom: '80px' }}>
                * 이미 생성된 대화방의 페르소나(Persona)는 <br /> 자동으로 업데이트되지 않습니다.
            </div>

            <button
                onClick={() => setIsCreateModalOpen(true)}
                style={{
                    position: 'absolute',
                    bottom: '20px',
                    right: '20px',
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                    border: 'none',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: 'var(--primary-foreground)'
                }}
            >
                <Plus size={28} />
            </button>

            {isCreateModalOpen && (
                <CreateRoomModal
                    novelId={novelId}
                    chapterId={chapterId}
                    onClose={() => setIsCreateModalOpen(false)}
                    onCreated={handleRoomCreated}
                />
            )}
        </div>
    );
}

// --- ChatRoom ---

interface ChatRoomProps {
    room: CharacterChatRoom;
}

function ChatRoom({ room }: ChatRoomProps) {
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
    }, [room.id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!inputText.trim() || loading) return;

        const text = inputText;
        setInputText('');
        setLoading(true);

        const tempUserId = Date.now();
        const streamingId = tempUserId + 1;
        setMessages(prev => [
            ...prev,
            { id: tempUserId, room_id: room.id, role: 'user', content: text, created_at: new Date().toISOString() },
            { id: streamingId, room_id: room.id, role: 'assistant', content: '', created_at: new Date().toISOString() }
        ]);

        try {
            await sendMessageStream(
                room.id,
                text,
                (userMsg) => {
                    setMessages(prev => prev.map(m => m.id === tempUserId ? userMsg : m));
                },
                (token) => {
                    setMessages(prev => prev.map(m =>
                        m.id === streamingId ? { ...m, content: m.content + token } : m
                    ));
                },
                (aiMsg) => {
                    setMessages(prev => prev.map(m => m.id === streamingId ? aiMsg : m));
                }
            );
        } catch (error) {
            console.error("Failed to send message:", error);
            setMessages(prev => prev.filter(m => m.id !== tempUserId && m.id !== streamingId));
            toast.error("메시지 전송 실패");
            setInputText(text);
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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'var(--secondary)' }}>
            {/* Chat Area */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--muted-foreground)', marginBottom: '10px', opacity: 0.8 }}>
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
                                    backgroundColor: 'var(--chat-assistant-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--chat-assistant-text)'
                                }}>
                                    {room.character_name.charAt(0)}
                                </div>
                            )}

                            <div style={{ maxWidth: '70%' }}>
                                {!isUser && (
                                    <div style={{ fontSize: '0.8rem', marginBottom: '4px', color: 'var(--foreground)' }}>
                                        {room.character_name}
                                    </div>
                                )}
                                <div style={{
                                    backgroundColor: isUser ? 'var(--primary)' : 'var(--chat-assistant-bg)',
                                    color: isUser ? 'var(--primary-foreground)' : 'var(--chat-assistant-text)',
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
                                    color: 'var(--muted-foreground)',
                                    opacity: 0.8,
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
                        <div style={{ backgroundColor: 'var(--chat-assistant-bg)', color: 'var(--chat-assistant-text)', padding: '8px 12px', borderRadius: '12px', fontSize: '0.8rem' }}>
                            ...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{ backgroundColor: 'var(--modal-bg)', padding: '10px', display: 'flex', gap: '8px', borderTop: '1px solid var(--border)' }}>
                <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="메시지를 입력하세요..."
                    style={{
                        flex: 1,
                        border: '1px solid var(--input-border)',
                        borderRadius: '4px',
                        padding: '8px',
                        resize: 'none',
                        height: '40px',
                        fontFamily: 'inherit',
                        backgroundColor: 'var(--input-bg)',
                        color: 'var(--input-text)'
                    }}
                />
                <button
                    onClick={handleSend}
                    disabled={loading || !inputText.trim()}
                    style={{
                        backgroundColor: 'var(--primary)',
                        border: '1px solid var(--input-border)',
                        borderRadius: '4px',
                        width: '50px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: loading ? 'var(--muted-foreground)' : 'var(--primary-foreground)'
                    }}
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    );
}

// --- Main Component: CharacterChatBot ---

interface CharacterChatWindowProps {
    onClose: () => void;
    novelId: number;
    chapterId?: number;
}

export function CharacterChatBot({ onClose, novelId, chapterId }: CharacterChatWindowProps) {
    const [activeRoom, setActiveRoom] = useState<CharacterChatRoom | null>(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setIsMenuOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const handleDeleteRoom = async () => {
        if (!activeRoom) return;
        try {
            await deleteRoom(activeRoom.id);
            setActiveRoom(null);
            setIsMenuOpen(false);
            toast.success("대화방이 삭제되었습니다.");
        } catch (error) {
            console.error("Failed to delete room:", error);
            toast.error("대화방 삭제 실패");
        }
    };

    const handleRoomUpdated = (updatedRoom: CharacterChatRoom) => {
        setActiveRoom(updatedRoom);
        setIsEditModalOpen(false);
    };

    return (
        <div className="character-chat-window" style={{
            position: 'fixed',
            bottom: '16px',
            right: '20px',
            width: '600px',
            height: '850px',
            backgroundColor: 'var(--modal-bg)',
            borderRadius: '16px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 1001,
            overflow: 'hidden',
            border: '1px solid var(--border)'
        }}>
            {/* Header */}
            <div className="chat-header" style={{
                padding: '16px',
                backgroundColor: 'var(--modal-header-bg)',
                color: 'var(--modal-header-text)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontWeight: 'bold',
                position: 'relative'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <button onClick={() => setActiveRoom(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'inherit' }}>
                            <ArrowLeft size={20} />
                        </button>
                    )}
                    <span>{activeRoom ? activeRoom.character_name : '캐릭터 대화'}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <div style={{ position: 'relative' }} ref={menuRef}>
                            <button
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', color: 'inherit' }}
                            >
                                <MoreVertical size={20} />
                            </button>

                            {isMenuOpen && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    right: 0,
                                    marginTop: '8px',
                                    backgroundColor: 'var(--modal-bg)',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                    zIndex: 10,
                                    minWidth: '150px',
                                    overflow: 'hidden',
                                    border: '1px solid var(--border)'
                                }}>
                                    <button
                                        onClick={() => {
                                            setIsEditModalOpen(true);
                                            setIsMenuOpen(false);
                                        }}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: 'var(--modal-bg)',
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: 'var(--foreground)'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--secondary)'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--modal-bg)'}
                                    >
                                        <SquarePen size={16} />
                                        페르소나 수정
                                    </button>
                                    <button
                                        onClick={handleDeleteRoom}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: 'var(--modal-bg)',
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: '#c62828',
                                            borderTop: '1px solid var(--border)'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--secondary)'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--modal-bg)'}
                                    >
                                        <Trash2 size={16} />
                                        채팅방 삭제
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>
                        <X size={20} />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {activeRoom ? (
                    <ChatRoom room={activeRoom} />
                ) : (
                    <RoomList novelId={novelId} chapterId={chapterId} onSelectRoom={setActiveRoom} />
                )}
            </div>

            {/* Edit Modal */}
            {isEditModalOpen && activeRoom && (
                <CreateRoomModal
                    novelId={novelId}
                    chapterId={chapterId}
                    initialData={activeRoom}
                    mode="edit"
                    onClose={() => setIsEditModalOpen(false)}
                    onUpdated={handleRoomUpdated}
                />
            )}
        </div>
    );
}
