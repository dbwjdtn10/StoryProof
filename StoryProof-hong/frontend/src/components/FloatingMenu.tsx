import { MessageCircle, MoreVertical, Settings, ShieldAlert, X } from 'lucide-react'; // ShieldAlert 아이콘 추가
import { useState } from 'react';
import { ChatInterface } from './ChatBot';

interface FloatingMenuProps {
    onNavigateToScene?: (sceneIndex: number) => void;
    onCheckConsistency?: () => void; // 설정 파괴 분석을 실행할 콜백 함수 추가
}

export function FloatingMenu({ onNavigateToScene, onCheckConsistency }: FloatingMenuProps) {
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

    // 설정 파괴 분석 버튼 클릭 핸들러
    const handleConsistencyClick = () => {
        console.log("분석 버튼 클릭됨!");
        if (onCheckConsistency) {
            onCheckConsistency(); // 백엔드 에이전트 호출 로직 실행
        } else {
            alert('설정 파괴 분석 로직이 연결되지 않았습니다.');
        }
        setIsMenuOpen(false); // 분석 시작 후 메뉴 닫기
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
                        
                        {/* 아이콘을 ShieldAlert(방패)로 변경하여 '보호/탐지' 의미 강조 */}
                        <button 
                            className="menu-option highlight-btn" 
                            onClick={handleConsistencyClick} 
                            title="설정파괴분석기"
                        >
                            <ShieldAlert size={20} color="#4F46E5" /> 
                        </button>
                        
                        <button className="menu-option" onClick={openChat} title="챗봇">
                            <MessageCircle size={20} />
                        </button>
                    </div>
                )}
                <button 
                    className={`floating-menu-btn ${isMenuOpen ? 'active' : ''}`} 
                    onClick={toggleMenu}
                >
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
                    height: '80vh', // 고정 높이 대신 반응형 높이 권장
                    maxHeight: '900px',
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
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
                        backgroundColor: '#1a1a1a', // 완전한 검은색보다 약간의 다크 그레이 권장
                        color: 'white'
                    }}>
                        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '600' }}>StoryProof 어시스턴트</h3>
                        <button className="chatbot-close" onClick={closeChat} style={{ color: 'white', background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}>
                            <X size={20} />
                        </button>
                    </div>
                    <div className="chatbot-content" style={{ flex: 1, overflow: 'hidden' }}>
                        <ChatInterface onNavigateToScene={onNavigateToScene} />
                    </div>
                </div>
            )}
        </>
    );
}