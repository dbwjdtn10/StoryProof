import React, { useState, useEffect } from 'react';
import { X, User, Mail, LogOut, Cpu, Check } from 'lucide-react';
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

    const models = [
        { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash (빠름)', provider: 'Google' },
        { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash (추천)', provider: 'Google' },
        { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro (정교함)', provider: 'Google' },
    ];

    useEffect(() => {
        if (isOpen) {
            fetchUserProfile();
        }
    }, [isOpen]);

    const fetchUserProfile = async () => {
        setIsLoading(true);
        try {
            const token = localStorage.getItem('token');
            const data = await request<UserProfile>('/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            setUser(data);
        } catch (error) {
            console.error("Failed to fetch profile:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleModelChange = (modelId: string) => {
        setSelectedModel(modelId);
        localStorage.setItem('llm_model', modelId);
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('userMode');
        // Simple redirect to refresh and hit the login screen in App.tsx
        window.location.href = '/';
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100">
                    <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                        <User className="w-5 h-5 text-indigo-600" />
                        환경설정
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <div className="p-6 space-y-8">
                    {/* User Section */}
                    <section>
                        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">계정 정보</h3>
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

                    {/* LLM Model Section */}
                    <section>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI 분석 모델</h3>
                            <span className="text-[10px] px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-bold">Active</span>
                        </div>
                        <div className="grid gap-2">
                            {models.map((model) => (
                                <button
                                    key={model.id}
                                    onClick={() => handleModelChange(model.id)}
                                    className={`flex items-center justify-between p-3 rounded-xl border transition-all ${selectedModel === model.id
                                            ? 'border-indigo-600 bg-indigo-50 shadow-sm'
                                            : 'border-gray-200 hover:border-indigo-300 hover:bg-gray-50'
                                        }`}
                                >
                                    <div className="flex items-center gap-3 text-left">
                                        <div className={`p-1.5 rounded-lg ${selectedModel === model.id ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-500'}`}>
                                            <Cpu className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <p className={`text-sm font-semibold ${selectedModel === model.id ? 'text-indigo-900' : 'text-gray-700'}`}>
                                                {model.name}
                                            </p>
                                            <p className="text-[10px] text-gray-400">{model.provider} AI</p>
                                        </div>
                                    </div>
                                    {selectedModel === model.id && (
                                        <Check className="w-5 h-5 text-indigo-600" />
                                    )}
                                </button>
                            ))}
                        </div>
                    </section>

                    {/* Footer / Logout */}
                    <div className="pt-4 mt-2">
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-bold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-colors border border-red-100"
                        >
                            <LogOut className="w-4 h-4" />
                            계정 로그아웃
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
