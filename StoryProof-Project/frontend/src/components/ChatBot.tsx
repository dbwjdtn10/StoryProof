import { MessageCircle, X, Send } from 'lucide-react';
import { useState } from 'react';

export function ChatBot() {
    const [isOpen, setIsOpen] = useState(false);
    const [message, setMessage] = useState('');

    const handleSend = () => {
        if (message.trim()) {
            // Handle send message
            console.log('Message:', message);
            setMessage('');
        }
    };

    return (
        <>
            {/* Chatbot Panel */}
            {isOpen && (
                <div className="chatbot-panel">
                    <div className="chatbot-header">
                        <div className="chatbot-header-content">
                            <MessageCircle size={20} />
                            <h3 className="chatbot-title">AI 어시스턴트</h3>
                        </div>
                        <button className="chatbot-close" onClick={() => setIsOpen(false)}>
                            <X size={20} />
                        </button>
                    </div>
                    <div className="chatbot-messages">
                        <div className="chatbot-message bot">
                            <p>안녕하세요! 무엇을 도와드릴까요?</p>
                        </div>
                    </div>
                    <div className="chatbot-input-area">
                        <input
                            type="text"
                            className="chatbot-input"
                            placeholder="메시지를 입력하세요..."
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                        />
                        <button className="chatbot-send" onClick={handleSend}>
                            <Send size={20} />
                        </button>
                    </div>
                </div>
            )}

            {/* Chatbot Toggle Button */}
            <button
                className="chatbot-toggle-btn"
                onClick={() => setIsOpen(!isOpen)}
                title="AI 어시스턴트"
            >
                {isOpen ? <X size={24} /> : <MessageCircle size={24} />}
            </button>
        </>
    );
}
