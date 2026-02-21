
import React, { useState, useEffect, useRef } from 'react';
import {
    X, ArrowLeft, MoreVertical, Trash2, SquarePen,
    Plus, Send, Sparkles
} from 'lucide-react';
import { toast } from 'sonner';
import {
    CharacterChatRoom, CharacterChatMessage,
    generatePersona, createRoom, getRooms, sendMessage, getMessages, updateRoom, deleteRoom
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
                // Update mode
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
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'var(--modal-bg)',
            color: 'var(--modal-text)',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            padding: '20px'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontWeight: 'bold' }}>{mode === 'create' ? '새 대화 시작' : '페르소나 수정'}</h3>
                <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)' }}>
                    <X size={20} strokeWidth={2.5} />
                </button>
            </div>

            {error && (
                <div style={{
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    color: '#dc2626',
                    padding: '10px',
                    borderRadius: '8px',
                    marginBottom: '10px',
                    fontSize: '0.9rem',
                    border: '1px solid rgba(220, 38, 38, 0.2)'
                }}>
                    {error}
                </div>
            )}

            {step === 'input' ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', fontSize: '0.9rem' }}>캐릭터 이름</label>
                        <input
                            type="text"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            placeholder="예: 셜록 홈즈"
                            maxLength={100}
                            style={{
                                width: '100%', padding: '12px', borderRadius: '8px',
                                border: '1px solid var(--input-border)',
                                fontSize: '1rem',
                                backgroundColor: 'var(--input-bg)',
                                color: 'var(--input-text)'
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
                            backgroundColor: 'var(--primary)',
                            color: 'var(--primary-foreground)',
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
                                <Sparkles size={18} strokeWidth={2.5} />
                                페르소나 생성
                            </>
                        )}
                    </button>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <label style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>페르소나 프롬프트 (수정 가능)</label>
                            <button
                                onClick={handleGenerate}
                                title="AI 자동 업데이트 (현재 분석 데이터 기반)"
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--muted-foreground)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem'
                                }}
                            >
                                <Sparkles size={14} strokeWidth={2.5} />
                                AI 자동 갱신
                            </button>
                        </div>
                        <textarea
                            value={personaPrompt}
                            onChange={(e) => setPersonaPrompt(e.target.value)}
                            maxLength={2000}
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
                                    color: 'var(--secondary-foreground)',
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
                                backgroundColor: 'var(--primary)',
                                color: 'var(--primary-foreground)',
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

    const fetchRooms = async () => {
        try {
            setLoading(true);
            const data = await getRooms(novelId, chapterId);
            setRooms(data);
        } catch (error) {
            console.error("Failed to fetch rooms:", error);
            toast.error("채팅방 목록을 불러오지 못했습니다.");
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
                                backgroundColor: 'var(--card)',
                                border: '1px solid var(--border)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px',
                                transition: 'background 0.2s',
                                color: 'var(--card-foreground)'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--secondary)'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--card)'}
                        >
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '50%',
                                backgroundColor: 'var(--secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <span style={{ fontWeight: 'bold', color: 'var(--secondary-foreground)' }}>
                                    {room.character_name.charAt(0)}
                                </span>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 'bold' }}>{room.character_name}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
                                    {new Date(room.updated_at || room.created_at).toLocaleDateString()}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Notice Footer */}
            <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.75rem', color: 'var(--muted-foreground)', paddingBottom: '80px' }}>
                * 이미 생성된 대화방의 페르소나(Persona)는 <br /> 자동으로 업데이트되지 않습니다.
            </div>

            {/* Floating Action Button for New Chat */}
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
                <Plus size={28} strokeWidth={2.5} />
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
            toast.error("메시지 기록을 불러오지 못했습니다.");
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
            setMessages(prev => {
                const filtered = prev.filter(m => m.id !== tempMsg.id);
                return [...filtered, ...newMessages];
            });
        } catch (error) {
            console.error("Failed to send message:", error);
            // Revert optimistic update
            setMessages(prev => prev.filter(m => m.id !== tempMsg.id));
            toast.error("메시지 전송 실패");
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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: 'var(--modal-bg)' }}>
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
                                    backgroundColor: 'var(--secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '0.8rem', fontWeight: 'bold', color: 'var(--secondary-foreground)'
                                }}>
                                    {room.character_name.charAt(0)}
                                </div>
                            )}

                            <div style={{ maxWidth: '75%' }}>
                                {!isUser && (
                                    <div style={{ fontSize: '0.8rem', marginBottom: '4px', color: 'var(--muted-foreground)' }}>
                                        {room.character_name}
                                    </div>
                                )}
                                <div style={{
                                    backgroundColor: isUser ? 'var(--primary)' : 'var(--chat-assistant-bg)',
                                    color: isUser ? 'var(--primary-foreground)' : 'var(--chat-assistant-text)',
                                    padding: '10px 14px',
                                    borderRadius: isUser ? '12px 0 12px 12px' : '0 12px 12px 12px',
                                    fontSize: '0.95rem',
                                    lineHeight: '1.5',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    border: isUser ? 'none' : '1px solid var(--border)'
                                }}>
                                    {msg.content}
                                </div>
                                <div style={{
                                    fontSize: '0.7rem',
                                    color: 'var(--muted-foreground)',
                                    marginTop: '4px',
                                    textAlign: isUser ? 'right'
                                        : 'left'
                                }}>
                                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                            </div>
                        </div>
                    );
                })}
                {loading && (
                    <div style={{ display: 'flex', justifyContent: 'flex-start', paddingLeft: '44px' }}>
                        <div style={{ backgroundColor: 'var(--input-bg)', padding: '8px 12px', borderRadius: '12px', fontSize: '0.8rem', color: 'var(--muted-foreground)', border: '1px solid var(--border)' }}>
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
                    maxLength={500}
                    style={{
                        flex: 1,
                        border: '1px solid var(--input-border)',
                        borderRadius: '8px',
                        padding: '10px',
                        resize: 'none',
                        height: '44px',
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
                        border: 'none',
                        borderRadius: '8px',
                        width: '50px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--primary-foreground)',
                        opacity: loading || !inputText.trim() ? 0.5 : 1
                    }}
                >
                    <Send size={18} strokeWidth={2.5} />
                </button>
            </div>
        </div>
    );
}

// --- Main Component: CharacterChatBot (formerly CharacterChatWindow) ---

interface CharacterChatWindowProps {
    onClose: () => void;
    novelId: number;
    chapterId?: number;
}

export function CharacterChatBot({ onClose, novelId, chapterId }: CharacterChatWindowProps) {
    const [activeRoom, setActiveRoom] = useState<CharacterChatRoom | null>(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [roomListKey, setRoomListKey] = useState(0);
    const menuRef = useRef<HTMLDivElement>(null);

    // Close menu when clicking outside
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

    const handleDeleteRoom = () => {
        if (!activeRoom) return;
        toast("정말로 이 대화방을 삭제하시겠습니까?", {
            action: {
                label: "삭제",
                onClick: async () => {
                    try {
                        await deleteRoom(activeRoom.id);
                        setActiveRoom(null);
                        setIsMenuOpen(false);
                        setRoomListKey(prev => prev + 1);
                    } catch (error) {
                        console.error("Failed to delete room:", error);
                        toast.error("대화방 삭제 실패");
                    }
                }
            },
            cancel: { label: "취소", onClick: () => {} }
        });
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
            border: '2px solid var(--modal-border)'
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
                position: 'relative',
                borderBottom: '1px solid var(--border)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <button onClick={() => setActiveRoom(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                            <ArrowLeft size={20} color="currentColor" strokeWidth={2.5} />
                        </button>
                    )}
                    <span>{activeRoom ? activeRoom.character_name : '캐릭터 대화'}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <div style={{ position: 'relative' }} ref={menuRef}>
                            <button
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', color: 'currentColor' }}
                            >
                                <MoreVertical size={20} strokeWidth={2.5} />
                            </button>

                            {isMenuOpen && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    right: 0,
                                    marginTop: '8px',
                                    backgroundColor: 'var(--popover)',
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
                                            border: 'none', background: 'transparent',
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: 'var(--popover-foreground)'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--secondary)'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                    >
                                        <SquarePen size={16} strokeWidth={2.5} />
                                        페르소나 수정
                                    </button>
                                    <button
                                        onClick={handleDeleteRoom}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: 'transparent',
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: 'var(--destructive)',
                                            borderTop: '1px solid var(--border)'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--secondary)'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                    >
                                        <Trash2 size={16} strokeWidth={2.5} />
                                        채팅방 삭제
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'currentColor' }}>
                        <X size={20} strokeWidth={2.5} />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {activeRoom ? (
                    <ChatRoom room={activeRoom} />
                ) : (
                    <RoomList key={roomListKey} novelId={novelId} chapterId={chapterId} onSelectRoom={setActiveRoom} />
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
