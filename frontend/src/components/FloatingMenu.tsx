import { MessageCircle, MoreVertical, Settings, FileText, X, User } from 'lucide-react';//HJE
import { useState } from 'react';
import { ChatInterface } from './ChatBot';
//HJE
import { CharacterChatWindow } from './CharacterChat/CharacterChatWindow';

interface FloatingMenuProps {
    onNavigateToScene?: (sceneIndex: number) => void;
    novelId?: number;
}

export function FloatingMenu({ onNavigateToScene, novelId }: FloatingMenuProps) {//HJE
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [isCharacterChatOpen, setIsCharacterChatOpen] = useState(false);//HJE

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const openChat = () => {
        setIsChatOpen(true);
        setIsMenuOpen(false);
        setIsCharacterChatOpen(false);
    };

    const openCharacterChat = () => {
        if (!novelId) {
            alert("소설 정보가 없어 캐릭터 챗봇을 열 수 없습니다.");
            return;
        }
        setIsCharacterChatOpen(true);
        setIsMenuOpen(false);
        setIsChatOpen(false);
    };
    //HJE
    const closeChat = () => {
        setIsChatOpen(false);
    };

    return (
        <>
            {/* Floating Menu Button */}
            <div className="floating-menu-container">
                {isMenuOpen && (
                    <div className="floating-menu-options">
                        <button className="menu-option" onClick={() => alert('환경설정')} title="환경설정">
                            <Settings size={20} />
                        </button>
                        <button className="menu-option" onClick={() => alert('설정파괴분석기')} title="설정파괴분석기">
                            <FileText size={20} />
                        </button>
                        <button className="menu-option" onClick={openCharacterChat} title="캐릭터 챗봇">
                            <User size={20} />
                        </button>
                        <button className="menu-option" onClick={openChat} title="AI 보조">
                            <MessageCircle size={20} />
                        </button>
                    </div>
                )}
                <button className="floating-menu-btn" onClick={toggleMenu}>
                    <MoreVertical size={24} />
                </button>
            </div>

            {/* Chatbot Modal */}
            {isChatOpen && (
                <div className="chatbot-modal" style={{
                    position: 'fixed',
                    bottom: '80px',
                    right: '20px',
                    width: '600px',
                    height: '900px',
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 1000,
                    overflow: 'hidden'
                }}>
                    <div className="chatbot-header" style={{
                        padding: '16px',
                        borderBottom: '1px solid #eee',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        backgroundColor: 'black',
                        color: 'white'
                    }}>
                        <h3 style={{ margin: 0, fontSize: '1.2rem' }}>AI 보조</h3>
                        <button className="chatbot-close" onClick={closeChat} style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer' }}>
                            <X size={20} />
                        </button>
                    </div>
                    <div className="chatbot-content" style={{ flex: 1, overflow: 'hidden' }}>
                        <ChatInterface onNavigateToScene={onNavigateToScene} />
                    </div>
                </div>
            )}

            {/* Character Chat Window */}
            {isCharacterChatOpen && novelId && (
                <CharacterChatWindow
                    novelId={novelId}
                    onClose={() => setIsCharacterChatOpen(false)}
                />
            )}

        </>
    );
}
