import { ArrowLeft, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, Users, Package, Clock } from 'lucide-react';
import { useState } from 'react';
import { FloatingMenu } from './FloatingMenu';
import { ThemeToggle } from './ThemeToggle';

interface ChapterDetailProps {
    fileName: string;
    onBack: () => void;
}

export function ChapterDetail({ fileName, onBack }: ChapterDetailProps) {
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isCharactersOpen, setIsCharactersOpen] = useState(true);
    const [isItemsOpen, setIsItemsOpen] = useState(false);
    const [isTimelineOpen, setIsTimelineOpen] = useState(false);

    const novelText = `앨리스는 언니 옆에 앉아 할일 없이 강둑에 앉아있는 게 지루해지기 시작했어요.
그러다 한두 번 언니가 읽고 있는 책에 눈길을 주기도 했지만 그림이나 대화 하나 없는 책이지 뭐예요.
"그림이나 대화도 없는 책이 무슨 소용이람?" 앨리스는 생각했어요.

그래서 앨리스는 (더운 날씨 때문에 머리가 멍해져서 졸리긴 했지만) 데이지 화환을 만드는 즐거움이 일어나서 데이지를 따러 가는 수고를 감수할 만한 가치가 있을지 곰곰이 생각하고 있었어요. 바로 그때 분홍색 눈을 한 흰 토끼 한 마리가 앨리스 가까이를 지나갔어요.

이건 그다지 놀라운 일이 아니었어요. 앨리스는 토끼가 혼잣말로 "이런, 이런! 늦겠어!"라고 말하는 걸 들었을 때도 그게 그렇게 이상하다고 생각하지 않았어요. (나중에 생각해 보니 이상하게 여겼어야 했지만, 그때는 모든 게 너무나 자연스러워 보였거든요.) 하지만 토끼가 실제로 조끼 주머니에서 시계를 꺼내 보더니 서둘러 달려가는 걸 보자, 앨리스는 벌떡 일어났어요. 조끼 주머니가 달린 토끼도, 거기서 꺼낼 시계를 가진 토끼도 본 적이 없다는 생각이 번뜩 스쳤거든요. 호기심에 불타 앨리스는 들판을 가로질러 토끼를 쫓아갔고, 토끼가 울타리 밑 큰 토끼 굴로 뛰어들어 가는 걸 보았어요.`;

    // Sample characters
    const characters = [
        { name: '앨리스', description: '호기심 많은 소녀, 이상한 나라로 떨어짐' },
        { name: '흰 토끼', description: '분홍색 눈을 가진 토끼, 항상 시간에 쫓김' },
        { name: '언니', description: '앨리스의 언니, 책을 읽고 있음' },
    ];

    // Sample items
    const items = [
        { name: '시계', description: '흰 토끼가 가지고 있던 회중시계' },
        { name: '책', description: '언니가 읽고 있던 그림 없는 책' },
        { name: '데이지 화환', description: '앨리스가 만들려고 했던 꽃 목걸이' },
    ];

    // Sample timeline
    const timeline = [
        { time: '오후', event: '앨리스가 언니 옆 강둑에 앉아 있음' },
        { time: '오후 (조금 후)', event: '흰 토끼가 지나가는 것을 목격' },
        { time: '오후 (직후)', event: '토끼를 따라 토끼 굴로 들어감' },
    ];

    return (
        <div className="chapter-detail-container">
            {/* Header */}
            <div className="chapter-detail-header">
                <button className="back-button" onClick={onBack}>
                    <ArrowLeft size={24} />
                </button>
                <h1 className="chapter-detail-title">{fileName}</h1>
            </div>

            {/* Main Layout */}
            <div className="chapter-detail-layout">
                {/* Sidebar */}
                <div className={`dictionary-sidebar ${isSidebarOpen ? 'open' : 'closed'}`}>
                    {/* Characters Section */}
                    <div className="sidebar-section">
                        <button
                            className="section-header"
                            onClick={() => setIsCharactersOpen(!isCharactersOpen)}
                        >
                            <div className="section-header-content">
                                <Users size={18} />
                                <h3 className="section-title">인물</h3>
                            </div>
                            {isCharactersOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isCharactersOpen && (
                            <div className="section-content">
                                {characters.map((character, index) => (
                                    <div key={index} className="section-item">
                                        <div className="item-name">{character.name}</div>
                                        <div className="item-description">{character.description}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Items Section */}
                    <div className="sidebar-section">
                        <button
                            className="section-header"
                            onClick={() => setIsItemsOpen(!isItemsOpen)}
                        >
                            <div className="section-header-content">
                                <Package size={18} />
                                <h3 className="section-title">아이템</h3>
                            </div>
                            {isItemsOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isItemsOpen && (
                            <div className="section-content">
                                {items.map((item, index) => (
                                    <div key={index} className="section-item">
                                        <div className="item-name">{item.name}</div>
                                        <div className="item-description">{item.description}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Timeline Section */}
                    <div className="sidebar-section">
                        <button
                            className="section-header"
                            onClick={() => setIsTimelineOpen(!isTimelineOpen)}
                        >
                            <div className="section-header-content">
                                <Clock size={18} />
                                <h3 className="section-title">타임라인</h3>
                            </div>
                            {isTimelineOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        </button>
                        {isTimelineOpen && (
                            <div className="section-content">
                                {timeline.map((event, index) => (
                                    <div key={index} className="section-item">
                                        <div className="item-name">{event.time}</div>
                                        <div className="item-description">{event.event}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Toggle Button */}
                <button
                    className="dictionary-toggle"
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                >
                    {isSidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
                </button>

                {/* Main Text Area */}
                <div className="text-area">
                    <div className="text-content">
                        <p className="novel-text">{novelText}</p>
                    </div>
                </div>
            </div>

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* Floating Menu - Settings, Analysis, Chatbot */}
            <FloatingMenu />
        </div>
    );
}
