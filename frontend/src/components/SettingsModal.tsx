import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X, User, Mail, LogOut, Check, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { request } from '../api/client';

interface UserProfile {
    username: string;
    email: string;
    mode: string;
}

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
    const [user, setUser] = useState<UserProfile | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedModel, setSelectedModel] = useState(
        localStorage.getItem('llm_model') || 'gemini-2.5-flash'
    );
    const [isModelDropdownOpen, setIsModelDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    const models = [
        { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash (빠름)', provider: 'Google' },
        { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash (추천)', provider: 'Google' },
        { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro (정교함)', provider: 'Google' },
        { id: 'gemini-2.0', name: 'Gemini 2.0 (균형)', provider: 'Google' },
        { id: 'gpt-4', name: 'GPT-4 (고품질)', provider: 'OpenAI' },
        { id: 'claude-3-opus', name: 'Claude 3 Opus (창의적)', provider: 'Anthropic' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo (경제적)', provider: 'OpenAI' },
    ];

    useEffect(() => {
        if (isOpen) {
            fetchUserProfile();
        }
    }, [isOpen]);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsModelDropdownOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchUserProfile = async () => {
        setIsLoading(true);
        try {
            const data = await request<UserProfile>('/auth/me');
            setUser(data);
        } catch (error) {
            console.error('Failed to fetch profile:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleModelChange = (modelId: string) => {
        setSelectedModel(modelId);
        localStorage.setItem('llm_model', modelId);
        setIsModelDropdownOpen(false);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('userMode');
        window.location.href = '/';
    };

    const handleDeleteAccount = () => {
        toast.info('계정 삭제 기능은 준비 중입니다.');
    };

    if (!isOpen) return null;

    const selectedModelName = models.find(m => m.id === selectedModel)?.name || selectedModel;

    return createPortal(
        <div
            className="fixed z-[9999] bg-white shadow-2xl overflow-hidden animate-in slide-in-from-bottom-5 fade-in duration-200"
            style={{
                bottom: '85px',
                right: '25px',
                width: '380px',
                maxHeight: '700px',
                display: 'flex',
                flexDirection: 'column',
                borderRadius: '16px',
                border: '1px solid #ddd',
                fontFamily: 'sans-serif'
            }}
        >
            <div className="w-full flex flex-col h-full">
                {/* Header */}
                <div style={{
                    padding: '16px',
                    backgroundColor: '#fee500',
                    color: '#3b1e1e',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontWeight: 'bold',
                    borderBottom: '1px solid rgba(0,0,0,0.05)'
                }}>
                    <h2 className="text-lg font-bold flex items-center gap-2 m-0">
                        <User className="w-5 h-5" color="#3b1e1e" />
                        환경설정
                    </h2>
                    <button
                        onClick={onClose}
                        aria-label="닫기"
                        title="닫기"
                        className="p-1 hover:opacity-70 transition-opacity rounded-full"
                        style={{ color: '#3b1e1e' }}
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="p-6 space-y-6 overflow-y-auto">
                    {/* User Section */}
                    <section>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">계정 정보</h3>
                        {isLoading ? (
                            <div className="animate-pulse space-y-3">
                                <div className="h-4 bg-gray-100 rounded w-3/4"></div>
                                <div className="h-4 bg-gray-100 rounded w-1/2"></div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-indigo-50 rounded-lg">
                                        <User className="w-5 h-5 text-indigo-600" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">{user?.username || '로딩 중...'}</p>
                                        <p className="text-xs text-gray-500">사용자 이름</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-blue-50 rounded-lg">
                                        <Mail className="w-5 h-5 text-blue-600" />
                                    </div>
                                    <div>
                                        <p className="text-sm font-medium text-gray-900">{user?.email || '로딩 중...'}</p>
                                        <p className="text-xs text-gray-500">이메일 계정</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </section>

                    <hr className="border-gray-100" />

                    {/* LLM Model Section */}
                    <section>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">LLM AI 모델 선택</h3>
                        <div className="relative" ref={dropdownRef}>
                            <button
                                onClick={() => setIsModelDropdownOpen(!isModelDropdownOpen)}
                                className="w-full flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-xl hover:bg-gray-100 transition-colors text-left"
                            >
                                <span className="text-sm font-medium text-gray-800">{selectedModelName}</span>
                                {isModelDropdownOpen
                                    ? <ChevronUp size={16} className="text-gray-500" />
                                    : <ChevronDown size={16} className="text-gray-500" />}
                            </button>

                            {isModelDropdownOpen && (
                                <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                                    {models.map((model) => (
                                        <button
                                            key={model.id}
                                            onClick={() => handleModelChange(model.id)}
                                            className="w-full text-left px-4 py-3 text-sm hover:bg-gray-50 flex items-center justify-between border-b border-gray-50 last:border-0"
                                        >
                                            <span className={`${selectedModel === model.id ? 'font-bold text-indigo-900' : 'text-gray-700'}`}>
                                                {model.name}
                                            </span>
                                            {selectedModel === model.id && <Check size={16} className="text-indigo-600" />}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </section>

                    <hr className="border-gray-100" />

                    {/* Account Management */}
                    <section>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">계정 관리</h3>
                        <p className="text-xs text-gray-500 mb-4">
                            계정과 관련된 모든 데이터를 영구적으로 삭제합니다. 이 작업은 되돌릴 수 없습니다.
                        </p>
                        <div className="space-y-3">
                            <button
                                onClick={handleDeleteAccount}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-bold text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors shadow-sm"
                            >
                                <Trash2 className="w-4 h-4" />
                                계정 삭제
                            </button>
                            <button
                                onClick={handleLogout}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-bold text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors shadow-sm"
                            >
                                <LogOut className="w-4 h-4" />
                                로그아웃
                            </button>
                        </div>
                    </section>
                </div>
            </div>
        </div>,
        document.body
    );
}
