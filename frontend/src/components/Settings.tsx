import { useState, useEffect } from "react";
import { LogOut, X, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { request } from "../api/client";
import "./Settings.css";

interface UserProfile {
    username: string;
    email: string;
    mode: string;
}

export function Settings({ onClose }: { onClose: () => void }) {
    const [userName, setUserName] = useState("");
    const [userEmail, setUserEmail] = useState("");
    const [selectedModel, setSelectedModel] = useState(
        localStorage.getItem('llm_model') || "gemini-2.0-flash"
    );
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    useEffect(() => {
        fetchUserProfile();
    }, []);

    useEffect(() => {
        if (selectedModel) {
            localStorage.setItem('llm_model', selectedModel);
        }
    }, [selectedModel]);

    const fetchUserProfile = async () => {
        try {
            const data = await request<UserProfile>('/auth/me');
            setUserName(data.username);
            setUserEmail(data.email);
        } catch (error) {
            console.error("Failed to fetch profile:", error);
            toast.error("프로필 정보를 불러올 수 없습니다.");
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('userMode');
        window.location.href = '/';
    };

    const handleDeleteAccount = () => {
        toast.info('계정 삭제 기능은 준비 중입니다.');
    };

    const models = [
        { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash (빠름)" },
        { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash (추천)" },
        { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro (정교함)" },
        { value: "gemini-2.0", label: "Gemini 2.0 (균형)" },
    ];

    return (
        <div className="settings-panel">
            <div className="settings-container">
                {/* Header */}
                <div className="settings-header">
                    <h2 className="settings-title">환경설정</h2>
                    <button onClick={onClose} className="close-button" aria-label="Close settings">
                        <X size={24} strokeWidth={2} />
                    </button>
                </div>

                <div className="settings-content">
                    {/* Profile Header */}
                    <div className="profile-section">
                        <div className="profile-header-text">
                            <h3 className="section-title">프로필 설정</h3>
                            <p className="section-description">계정 정보 및 AI 모델 설정을 관리하세요.</p>
                        </div>
                    </div>

                    {/* Form Fields */}
                    <div className="settings-form">
                        <div className="form-group">
                            <label className="form-label">이름</label>
                            <input
                                className="form-input"
                                value={userName}
                                onChange={(e) => setUserName(e.target.value)}
                                placeholder="이름을 입력하세요"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">이메일</label>
                            <input
                                className="form-input disabled"
                                value={userEmail}
                                disabled
                            />
                            <p className="input-note">계정 이메일은 변경할 수 없습니다</p>
                        </div>

                        <div className="form-group">
                            <label className="form-label">LLM AI 모델 선택</label>
                            <div className="select-wrapper">
                                <button
                                    className={`select-button ${isDropdownOpen ? 'active' : ''}`}
                                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                                >
                                    <span>
                                        {models.find(m => m.value === selectedModel)?.label || selectedModel}
                                    </span>
                                    <ChevronDown size={16} className={`dropdown-icon ${isDropdownOpen ? 'open' : ''}`} />
                                </button>

                                {isDropdownOpen && (
                                    <div className="select-dropdown">
                                        {models.map((model) => (
                                            <button
                                                key={model.value}
                                                className={`select-option ${selectedModel === model.value ? 'selected' : ''}`}
                                                onClick={() => {
                                                    setSelectedModel(model.value);
                                                    setIsDropdownOpen(false);
                                                }}
                                            >
                                                {model.label}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <p className="model-note">선택한 AI 모델로 집필 도움을 받을 수 있습니다</p>
                        </div>

                        {/* Account Deletion */}
                        <div className="danger-zone">
                            <h3 className="danger-title">계정 관리</h3>
                            <p className="danger-description">
                                계정과 관련된 모든 데이터를 영구적으로 삭제합니다.
                            </p>
                            <button className="btn btn-destructive" onClick={handleDeleteAccount}>
                                계정 삭제
                            </button>
                        </div>
                    </div>
                </div>

                {/* Footer Buttons */}
                <div className="settings-footer">
                    <button className="btn btn-outline" onClick={handleLogout}>
                        <LogOut size={18} />
                        로그아웃
                    </button>
                </div>
            </div>
        </div>
    );
}
