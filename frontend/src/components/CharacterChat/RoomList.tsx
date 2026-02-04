//HJE

import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare } from 'lucide-react';
import { getRooms, CharacterChatRoom } from '../../api/characterChat';
import { CreateRoomModal } from './CreateRoomModal.tsx';

interface RoomListProps {
    novelId: number;
    onSelectRoom: (room: CharacterChatRoom) => void;
}

export function RoomList({ novelId, onSelectRoom }: RoomListProps) {
    const [rooms, setRooms] = useState<CharacterChatRoom[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    const fetchRooms = async () => {
        try {
            setLoading(true);
            const data = await getRooms(novelId);
            setRooms(data);
        } catch (error) {
            console.error("Failed to fetch rooms:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRooms();
    }, [novelId]);

    const handleRoomCreated = (newRoom: CharacterChatRoom) => {
        setRooms([newRoom, ...rooms]);
        setIsCreateModalOpen(false);
        onSelectRoom(newRoom);
    };

    return (
        <div style={{ padding: '16px', height: '100%', overflowY: 'auto', backgroundColor: '#fff' }}>
            {loading ? (
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>로딩 중...</div>
            ) : rooms.length === 0 ? (
                <div style={{ textAlign: 'center', marginTop: '100px', color: '#999' }}>
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
                                backgroundColor: '#f9f9f9',
                                border: '1px solid #eee',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '12px', // Moved gap here
                                transition: 'background 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f0f0f0'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f9f9f9'}
                        >
                            <div style={{
                                width: '40px', height: '40px', borderRadius: '50%',
                                backgroundColor: '#e0e0e0', display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <span style={{ fontWeight: 'bold', color: '#666' }}>
                                    {room.character_name.charAt(0)}
                                </span>
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 'bold' }}>{room.character_name}</div>
                                <div style={{ fontSize: '0.8rem', color: '#999' }}>
                                    {new Date(room.updated_at || room.created_at).toLocaleDateString()}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

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
                    backgroundColor: '#fee500',
                    border: 'none',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    color: '#3b1e1e'
                }}
            >
                <Plus size={28} />
            </button>

            {isCreateModalOpen && (
                <CreateRoomModal
                    novelId={novelId}
                    onClose={() => setIsCreateModalOpen(false)}
                    onCreated={handleRoomCreated}
                />
            )}
        </div>
    );
}
