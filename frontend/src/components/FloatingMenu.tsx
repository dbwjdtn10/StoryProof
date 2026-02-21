import { MessageCircle, MoreVertical, ShieldAlert, X, Sparkles, MessageSquare, Users, Settings as SettingsIcon, Network } from 'lucide-react';
import { useState } from 'react';
import { ChatInterface } from './ChatBot';
import { useTheme } from '../contexts/ThemeContext';
import '../chatbot.css';

interface FloatingMenuProps {
    onNavigateToScene?: (sceneIndex: number) => void;
    onCheckConsistency?: () => void;
    onPredictStory?: () => void;
    onOpenCharacterChat?: () => void;
    onOpenSettings?: () => void;
    onOpenRelGraph?: () => void;
    novelId?: number;
    chapterId?: number;
    mode?: 'reader' | 'writer';
}

export function FloatingMenu({ onNavigateToScene, onCheckConsistency, onPredictStory, onOpenCharacterChat, onOpenSettings, onOpenRelGraph, novelId, chapterId, mode = 'writer' }: FloatingMenuProps) {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const { theme } = useTheme();

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
                        <button className="menu-option btn-purple" onClick={() => {
                            if (onPredictStory) onPredictStory();
                            setIsMenuOpen(false);
                        }} title="스토리 예측 (What-If)">
                            <Sparkles size={20} strokeWidth={2.5} />
                        </button>
                        <button className="menu-option" onClick={() => {
                            if (onOpenRelGraph) onOpenRelGraph();
                            setIsMenuOpen(false);
                        }} title="인물 관계도" style={{ background: '#10B981', color: '#fff', border: 'none' }}>
                            <Network size={20} strokeWidth={2.5} />
                        </button>
                        {mode !== 'reader' && (
                            <>
                                <button className="menu-option btn-blue" onClick={handleConsistencyClick} title="설정파괴분석기">
                                    <ShieldAlert size={20} strokeWidth={2.5} />
                                </button>
                            </>
                        )}
                        <button className="menu-option btn-brown-med" onClick={openChat} title="챗봇">
                            <MessageCircle size={20} strokeWidth={2.5} />
                        </button>
                        <button className="menu-option btn-brown-rich" onClick={() => {
                            if (onOpenCharacterChat) onOpenCharacterChat();
                            setIsMenuOpen(false);
                        }} title="캐릭터 챗봇">
                            <Users size={20} strokeWidth={2.5} />
                        </button>
                        <button className="menu-option btn-brown-dark" onClick={() => {
                            if (onOpenSettings) onOpenSettings();
                            setIsMenuOpen(false);
                        }} title="환경설정">
                            <SettingsIcon size={20} strokeWidth={2.5} />
                        </button>
                    </div>
                )}
                <button
                    className="floating-menu-btn"
                    onClick={toggleMenu}
                    style={{
                        backgroundColor: theme === 'sepia' ? 'var(--color-dark-brown)' : 'var(--primary)',
                        color: 'var(--primary-foreground)'
                    }}
                >
                    <MoreVertical size={24} strokeWidth={2.5} />
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
                        borderBottom: '1px solid var(--border)',
                        display: 'flex',
                        justifyContent: 'flex-end',
                        alignItems: 'center',
                        backgroundColor: 'var(--modal-header-bg)',
                        color: 'var(--modal-header-text)'
                    }}>

                        <button className="chatbot-close" onClick={closeChat} style={{ color: 'currentColor', background: 'none', border: 'none', cursor: 'pointer' }}>
                            <X size={20} strokeWidth={2.5} />
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
