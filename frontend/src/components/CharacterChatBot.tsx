
import React, { useState, useEffect, useRef } from 'react';
import {
    X, ArrowLeft, MoreVertical, Trash2, SquarePen,
    Plus, Send, Sparkles
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../contexts/ThemeContext';
import {
    CharacterChatRoom, CharacterChatMessage,
    generatePersona, createRoom, getRooms, sendMessageStream, getMessages, updateRoom, deleteRoom
} from '../api/characterChat';

// ------------------------------------------------------------------
// Theme Colors
// ------------------------------------------------------------------

type ThemeColors = {
    container: string;
    header: string;
    headerText: string;
    chatBg: string;
    userBubble: string;
    userBubbleText: string;
    aiBubble: string;
    aiBubbleText: string;
    inputArea: string;
    inputBorder: string;
    inputText: string;
    roomListBg: string;
    roomItemBg: string;
    roomItemHover: string;
    dropdown: string;
    dropdownHover: string;
    text: string;
    subText: string;
    border: string;
    avatarBg: string;
    avatarText: string;
    errorBg: string;
    errorText: string;
    backBtnBg: string;
    backBtnText: string;
};

const THEME_COLORS: Record<string, ThemeColors> = {
    light: {
        container: '#ffffff',
        header: '#fee500',
        headerText: '#3b1e1e',
        chatBg: '#b2c7da',
        userBubble: '#fee500',
        userBubbleText: '#3b1e1e',
        aiBubble: '#ffffff',
        aiBubbleText: '#333333',
        inputArea: '#ffffff',
        inputBorder: '#dddddd',
        inputText: '#333333',
        roomListBg: '#ffffff',
        roomItemBg: '#f9f9f9',
        roomItemHover: '#f0f0f0',
        dropdown: '#ffffff',
        dropdownHover: '#f5f5f5',
        text: '#333333',
        subText: '#999999',
        border: '#eeeeee',
        avatarBg: '#e0e0e0',
        avatarText: '#666666',
        errorBg: '#ffebee',
        errorText: '#c62828',
        backBtnBg: '#f0f0f0',
        backBtnText: '#333333',
    },
    sepia: {
        container: '#f5ede0',
        header: '#c9973a',
        headerText: '#2d1a0a',
        chatBg: '#c4b09a',
        userBubble: '#c9973a',
        userBubbleText: '#2d1a0a',
        aiBubble: '#f5ede0',
        aiBubbleText: '#3b2d1f',
        inputArea: '#f5ede0',
        inputBorder: '#c4a87a',
        inputText: '#3b2d1f',
        roomListBg: '#f5ede0',
        roomItemBg: '#ede0cc',
        roomItemHover: '#dfd0b8',
        dropdown: '#f5ede0',
        dropdownHover: '#ede0cc',
        text: '#3b2d1f',
        subText: '#7a6048',
        border: '#c4a87a',
        avatarBg: '#d4c0a0',
        avatarText: '#5a4020',
        errorBg: '#ffeedd',
        errorText: '#8b3a10',
        backBtnBg: '#ede0cc',
        backBtnText: '#3b2d1f',
    },
    dark: {
        container: '#1e1e2e',
        header: '#c9a227',
        headerText: '#1a1a1a',
        chatBg: '#16213e',
        userBubble: '#c9a227',
        userBubbleText: '#1a1a1a',
        aiBubble: '#2a2a40',
        aiBubbleText: '#e8e8f0',
        inputArea: '#1e1e2e',
        inputBorder: '#3a3a55',
        inputText: '#e8e8f0',
        roomListBg: '#1e1e2e',
        roomItemBg: '#2a2a40',
        roomItemHover: '#3a3a55',
        dropdown: '#2a2a40',
        dropdownHover: '#3a3a55',
        text: '#e8e8f0',
        subText: '#888899',
        border: '#3a3a55',
        avatarBg: '#3a3a55',
        avatarText: '#ccccdd',
        errorBg: '#3d1a1a',
        errorText: '#ff8080',
        backBtnBg: '#2a2a40',
        backBtnText: '#e8e8f0',
    },
};

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
    const { theme } = useTheme();
    const c = THEME_COLORS[theme] || THEME_COLORS.light;
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
            backgroundColor: c.container,
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            padding: '20px'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                <h3 style={{ margin: 0, color: c.text }}>{mode === 'create' ? '새 대화 시작' : '페르소나 수정'}</h3>
                <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: c.text }}>
                    <X size={20} />
                </button>
            </div>

            {error && (
                <div style={{
                    backgroundColor: c.errorBg,
                    color: c.errorText,
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
                        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold', color: c.text }}>캐릭터 이름</label>
                        <input
                            type="text"
                            value={characterName}
                            onChange={(e) => setCharacterName(e.target.value)}
                            placeholder="예: 셜록 홈즈"
                            style={{
                                width: '100%', padding: '12px', borderRadius: '8px',
                                border: `1px solid ${c.inputBorder}`,
                                fontSize: '1rem',
                                backgroundColor: c.inputArea,
                                color: c.inputText,
                                boxSizing: 'border-box'
                            }}
                        />
                        <p style={{ fontSize: '0.8rem', color: c.subText, marginTop: '4px' }}>
                            * 분석된 데이터에 있는 캐릭터 이름을 입력하세요.
                        </p>
                    </div>

                    <button
                        onClick={handleGenerate}
                        disabled={loading || !characterName}
                        style={{
                            backgroundColor: c.header,
                            color: c.headerText,
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
                            <label style={{ fontWeight: 'bold', color: c.text }}>페르소나 프롬프트 (수정 가능)</label>
                            <button
                                onClick={handleGenerate}
                                title="AI 자동 업데이트 (현재 분석 데이터 기반)"
                                style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: c.subText, display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem'
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
                                border: `1px solid ${c.inputBorder}`,
                                fontSize: '0.9rem',
                                resize: 'none',
                                fontFamily: 'monospace',
                                backgroundColor: c.inputArea,
                                color: c.inputText
                            }}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                        {mode !== 'edit' && (
                            <button
                                onClick={() => setStep('input')}
                                style={{
                                    flex: 1,
                                    backgroundColor: c.backBtnBg,
                                    color: c.backBtnText,
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
                                backgroundColor: c.header,
                                color: c.headerText,
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
    const { theme } = useTheme();
    const c = THEME_COLORS[theme] || THEME_COLORS.light;
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
        <div style={{ padding: '16px', height: '100%', overflowY: 'auto', backgroundColor: c.roomListBg }}>
            {loading ? (
                <div style={{ textAlign: 'center', padding: '20px', color: c.subText }}>로딩 중...</div>
            ) : rooms.length === 0 ? (
                <div style={{ textAlign: 'center', marginTop: '100px', color: c.subText }}>
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
                                backgroundColor: roomHover === room.id ? c.roomItemHover : c.roomItemBg,
                                border: `1px solid ${c.border}`,
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
                                backgroundColor: c.avatarBg, display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <span style={{ fontWeight: 'bold', color: c.avatarText }}>
                                    {room.character_name.charAt(0)}
                                </span>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 'bold', color: c.text }}>{room.character_name}</div>
                                <div style={{ fontSize: '0.8rem', color: c.subText }}>
                                    {new Date(room.updated_at || room.created_at).toLocaleDateString()}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.75rem', color: c.subText, paddingBottom: '80px' }}>
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
                    backgroundColor: c.header,
                    border: 'none',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: c.headerText
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
    const { theme } = useTheme();
    const c = THEME_COLORS[theme] || THEME_COLORS.light;
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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: c.chatBg }}>
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
                                    backgroundColor: c.aiBubble, display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '0.8rem', fontWeight: 'bold', color: c.aiBubbleText
                                }}>
                                    {room.character_name.charAt(0)}
                                </div>
                            )}

                            <div style={{ maxWidth: '70%' }}>
                                {!isUser && (
                                    <div style={{ fontSize: '0.8rem', marginBottom: '4px', color: '#ffffff' }}>
                                        {room.character_name}
                                    </div>
                                )}
                                <div style={{
                                    backgroundColor: isUser ? c.userBubble : c.aiBubble,
                                    color: isUser ? c.userBubbleText : c.aiBubbleText,
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
                                    color: '#ffffff',
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
                        <div style={{ backgroundColor: c.aiBubble, color: c.aiBubbleText, padding: '8px 12px', borderRadius: '12px', fontSize: '0.8rem' }}>
                            ...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{ backgroundColor: c.inputArea, padding: '10px', display: 'flex', gap: '8px', borderTop: `1px solid ${c.border}` }}>
                <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="메시지를 입력하세요..."
                    style={{
                        flex: 1,
                        border: `1px solid ${c.inputBorder}`,
                        borderRadius: '4px',
                        padding: '8px',
                        resize: 'none',
                        height: '40px',
                        fontFamily: 'inherit',
                        backgroundColor: c.inputArea,
                        color: c.inputText
                    }}
                />
                <button
                    onClick={handleSend}
                    disabled={loading || !inputText.trim()}
                    style={{
                        backgroundColor: c.header,
                        border: `1px solid ${c.inputBorder}`,
                        borderRadius: '4px',
                        width: '50px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: loading ? c.subText : c.headerText
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
    const { theme } = useTheme();
    const c = THEME_COLORS[theme] || THEME_COLORS.light;
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
            backgroundColor: c.container,
            borderRadius: '16px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            zIndex: 1001,
            overflow: 'hidden',
            border: `1px solid ${c.border}`
        }}>
            {/* Header */}
            <div className="chat-header" style={{
                padding: '16px',
                backgroundColor: c.header,
                color: c.headerText,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontWeight: 'bold',
                position: 'relative'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <button onClick={() => setActiveRoom(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                            <ArrowLeft size={20} color={c.headerText} />
                        </button>
                    )}
                    <span>{activeRoom ? activeRoom.character_name : '캐릭터 대화'}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <div style={{ position: 'relative' }} ref={menuRef}>
                            <button
                                onClick={() => setIsMenuOpen(!isMenuOpen)}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex' }}
                            >
                                <MoreVertical size={20} color={c.headerText} />
                            </button>

                            {isMenuOpen && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    right: 0,
                                    marginTop: '8px',
                                    backgroundColor: c.dropdown,
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                    zIndex: 10,
                                    minWidth: '150px',
                                    overflow: 'hidden',
                                    border: `1px solid ${c.border}`
                                }}>
                                    <button
                                        onClick={() => {
                                            setIsEditModalOpen(true);
                                            setIsMenuOpen(false);
                                        }}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: c.dropdown,
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: c.text
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = c.dropdownHover}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = c.dropdown}
                                    >
                                        <SquarePen size={16} />
                                        페르소나 수정
                                    </button>
                                    <button
                                        onClick={handleDeleteRoom}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: c.dropdown,
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: '#c62828',
                                            borderTop: `1px solid ${c.border}`
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = c.dropdownHover}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = c.dropdown}
                                    >
                                        <Trash2 size={16} />
                                        채팅방 삭제
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                        <X size={20} color={c.headerText} />
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
