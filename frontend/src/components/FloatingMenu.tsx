import { MessageCircle, MoreVertical, Settings, FileText, X } from 'lucide-react';
import { useState } from 'react';
import { ChatInterface } from './ChatBot';
import '../chatbot.css';

interface FloatingMenuProps {
    onNavigateToScene?: (sceneIndex: number) => void;
    novelId?: number;
    chapterId?: number;
}

export function FloatingMenu({ onNavigateToScene, novelId, chapterId }: FloatingMenuProps) {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    const openChat = () => {
        setIsChatOpen(true);
        setIsMenuOpen(false);
    };

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
                        <button className="menu-option" onClick={openChat} title="챗봇">
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
                    bottom: '15px',
                    right: '25px',
                    width: '650px',
                    height: '850px',
                    borderRadius: '1rem',
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
                        justifyContent: 'flex-end',
                        alignItems: 'center',
                        backgroundColor: 'black',
                        color: 'white'
                    }}>

                        <button className="chatbot-close" onClick={closeChat} style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer' }}>
                            <X size={20} />
                        </button>
                    </div>
                    <div className="chatbot-content" style={{ flex: 1, overflow: 'hidden' }}>
                        <ChatInterface onNavigateToScene={onNavigateToScene} novelId={novelId} chapterId={chapterId} />
                    </div>
                </div>
            )}
        </>
    );
}
