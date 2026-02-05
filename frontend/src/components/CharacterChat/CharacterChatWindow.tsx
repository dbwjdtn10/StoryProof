import React, { useState, useEffect, useRef } from 'react';
import { X, ArrowLeft, MoreVertical, Trash2, SquarePen, AlertTriangle } from 'lucide-react';
import { RoomList } from './RoomList.tsx';
import { ChatRoom } from './ChatRoom.tsx';
import { CreateRoomModal } from './CreateRoomModal.tsx';
import { CharacterChatRoom, deleteRoom } from '../../api/characterChat';

interface CharacterChatWindowProps {
    onClose: () => void;
    novelId: number;
}

export function CharacterChatWindow({ onClose, novelId }: CharacterChatWindowProps) {
    const [activeRoom, setActiveRoom] = useState<CharacterChatRoom | null>(null);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
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

    const handleDeleteRoom = async () => {
        if (!activeRoom) return;
        if (confirm("정말로 이 대화방을 삭제하시겠습니까?")) {
            try {
                await deleteRoom(activeRoom.id);
                setActiveRoom(null);
                setIsMenuOpen(false);
            } catch (error) {
                console.error("Failed to delete room:", error);
                alert("대화방 삭제 실패");
            }
        }
    };

    const handleRoomUpdated = (updatedRoom: CharacterChatRoom) => {
        setActiveRoom(updatedRoom);
        setIsEditModalOpen(false);
    };

    return (
        <div className="character-chat-window" style={{
            position: 'fixed',
            bottom: '80px',
            right: '20px',
            width: '600px',
            height: '900px',
            backgroundColor: 'white',
            borderRadius: '16px', // Also matching ChatBot.tsx '1rem'
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)', // Matching ChatBot.tsx
            display: 'flex',
            flexDirection: 'column',
            zIndex: 1001,
            overflow: 'hidden',
            border: '1px solid #eee'
        }}>
            {/* Header */}
            <div className="chat-header" style={{
                padding: '16px',
                backgroundColor: '#fee500', // Kakao yellow-ish
                color: '#3b1e1e',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontWeight: 'bold',
                position: 'relative'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <button onClick={() => setActiveRoom(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                            <ArrowLeft size={20} color="#3b1e1e" />
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
                                <MoreVertical size={20} color="#3b1e1e" />
                            </button>

                            {isMenuOpen && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    right: 0,
                                    marginTop: '8px',
                                    backgroundColor: 'white',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                    zIndex: 10,
                                    minWidth: '150px',
                                    overflow: 'hidden'
                                }}>
                                    <button
                                        onClick={() => {
                                            setIsEditModalOpen(true);
                                            setIsMenuOpen(false);
                                        }}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: 'white',
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: '#333'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                                    >
                                        <SquarePen size={16} />
                                        페르소나 수정
                                    </button>
                                    <button
                                        onClick={handleDeleteRoom}
                                        style={{
                                            display: 'flex', alignItems: 'center', gap: '8px',
                                            width: '100%', padding: '12px 16px',
                                            border: 'none', background: 'white',
                                            cursor: 'pointer', textAlign: 'left',
                                            fontSize: '0.9rem', color: '#c62828',
                                            borderTop: '1px solid #eee'
                                        }}
                                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                                    >
                                        <Trash2 size={16} />
                                        채팅방 삭제
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                        <X size={20} color="#3b1e1e" />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {activeRoom ? (
                    <ChatRoom room={activeRoom} />
                ) : (
                    <RoomList novelId={novelId} onSelectRoom={setActiveRoom} />
                )}
            </div>

            {/* Edit Modal */}
            {isEditModalOpen && activeRoom && (
                <CreateRoomModal
                    novelId={novelId}
                    initialData={activeRoom}
                    mode="edit"
                    onClose={() => setIsEditModalOpen(false)}
                    onUpdated={handleRoomUpdated}
                />
            )}
        </div>
    );
}
