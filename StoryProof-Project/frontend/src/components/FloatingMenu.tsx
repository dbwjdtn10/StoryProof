import { MessageCircle, MoreVertical, Settings, FileText, X } from 'lucide-react';
import { useState } from 'react';

export function FloatingMenu() {
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
                <div className="chatbot-modal">
                    <div className="chatbot-header">
                        <h3>챗봇</h3>
                        <button className="chatbot-close" onClick={closeChat}>
                            <X size={20} />
                        </button>
                    </div>
                    <div className="chatbot-content">
                        <p>챗봇 기능이 여기에 표시됩니다.</p>
                    </div>
                </div>
            )}
        </>
    );
}
