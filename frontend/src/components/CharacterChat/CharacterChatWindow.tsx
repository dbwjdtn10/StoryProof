//HJE//HJE
import React, { useState, useEffect } from 'react';
import { X, ArrowLeft } from 'lucide-react';
import { RoomList } from './RoomList.tsx';
import { ChatRoom } from './ChatRoom.tsx';
import { CharacterChatRoom } from '../../api/characterChat';

interface CharacterChatWindowProps {
    onClose: () => void;
    novelId: number;
}

export function CharacterChatWindow({ onClose, novelId }: CharacterChatWindowProps) {
    const [activeRoom, setActiveRoom] = useState<CharacterChatRoom | null>(null);

    return (
        <div className="character-chat-window" style={{
            position: 'fixed',
            bottom: '80px',
            right: '25px', // Offset slightly from general chatbot if needed, or overlay
            width: '400px',
            height: '600px',
            backgroundColor: 'white',
            borderRadius: '20px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
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
                fontWeight: 'bold'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {activeRoom && (
                        <button onClick={() => setActiveRoom(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                            <ArrowLeft size={20} color="#3b1e1e" />
                        </button>
                    )}
                    <span>{activeRoom ? activeRoom.character_name : '캐릭터 대화'}</span>
                </div>
                <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                    <X size={20} color="#3b1e1e" />
                </button>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {activeRoom ? (
                    <ChatRoom room={activeRoom} />
                ) : (
                    <RoomList novelId={novelId} onSelectRoom={setActiveRoom} />
                )}
            </div>
        </div>
    );
}
