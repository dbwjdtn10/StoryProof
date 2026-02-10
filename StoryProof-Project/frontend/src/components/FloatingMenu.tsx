import { MessageCircle, MoreVertical, Settings, ShieldAlert, X, Sparkles, MessageSquare } from 'lucide-react';
import { useState } from 'react';
import { ChatInterface } from './ChatBot';
import '../chatbot.css';

interface FloatingMenuProps {
    onNavigateToScene?: (sceneIndex: number) => void;
    onCheckConsistency?: () => void;
    onPredictStory?: () => void;
    onOpenCharacterChat?: () => void;
    novelId?: number;
    chapterId?: number;
    mode?: 'reader' | 'writer';
}

export function FloatingMenu({ onNavigateToScene, onCheckConsistency, onPredictStory, onOpenCharacterChat, novelId, chapterId, mode = 'writer' }: FloatingMenuProps) {
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

    const handleConsistencyClick = () => {
        if (onCheckConsistency) {
            onCheckConsistency();
        }
        setIsMenuOpen(false);
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
                        {mode !== 'reader' && (
                            <>
                                <button className="menu-option highlight-btn-purple" onClick={() => {
                                    if (onPredictStory) onPredictStory();
                                    setIsMenuOpen(false);
                                }} title="스토리 예측 (What-If)" style={{ backgroundColor: '#EDE9FE', color: '#7C3AED' }}>
                                    <Sparkles size={20} />
                                </button>
                                <button className="menu-option highlight-btn" onClick={handleConsistencyClick} title="설정파괴분석기">
                                    <ShieldAlert size={20} color="#4F46E5" />
                                </button>
                            </>
                        )}
                        <button className="menu-option" onClick={openChat} title="챗봇">
                            <MessageCircle size={20} />
                        </button>
                        <button className="menu-option" onClick={() => {
                            if (onOpenCharacterChat) onOpenCharacterChat();
                            setIsMenuOpen(false);
                        }} title="캐릭터 챗봇">
                            <MessageSquare size={20} />
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
