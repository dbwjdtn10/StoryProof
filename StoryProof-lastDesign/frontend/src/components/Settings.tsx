import { useState, useEffect } from "react";
import {
  LogIn,
  LogOut,
  X,
  ChevronDown,
} from "lucide-react";
import { request } from "../api/client";
import "./Settings.css";

interface UserProfile {
  username: string;
  email: string;
  mode: string;
}

export function Settings({ onClose }: { onClose: () => void }) {
  const [userName, setUserName] = useState("박준형");
  const [userEmail, setUserEmail] = useState("abccj0497@bu.ac.kr");
  const [selectedModel, setSelectedModel] = useState(
    localStorage.getItem('llm_model') || "gemini-2.0-flash"
  );
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Initial Fetch & Effects
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
      const token = localStorage.getItem('token');
      if (!token) return;
      const data = await request<UserProfile>('/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setUserName(data.username);
      setUserEmail(data.email);
    } catch (error) {
      console.error("Failed to fetch profile:", error);
      setUserName("박준형");
      setUserEmail("abccj0497@bu.ac.kr");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userMode');
    window.location.href = '/';
  };

  const handleDeleteAccount = () => {
    if (confirm('정말로 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      alert('기능 준비 중입니다.');
    }
  };

  const models = [
    { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash (빠름)" },
    { value: "gemini-2.0", label: "Gemini 2.0 (균형)" },
    { value: "gpt-4", label: "GPT-4 (고품질)" },
    { value: "claude-3", label: "Claude 3 Opus (창의적)" },
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
              <p className="input-note">
                계정 이메일은 변경할 수 없습니다
              </p>
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
              <p className="model-note">
                선택한 AI 모델로 집필 도움을 받을 수 있습니다
              </p>
            </div>

            {/* Account Deletion */}
            <div className="danger-zone">
              <h3 className="danger-title">계정 관리</h3>
              <p className="danger-description">
                계정과 관련된 모든 데이터를 영구적으로 삭제합니다.
              </p>
              <button
                className="btn btn-destructive"
                onClick={handleDeleteAccount}
              >
                계정 삭제
              </button>
            </div>
          </div>
        </div>

        {/* Footer Buttons */}
        <div className="settings-footer">
          <button
            className="btn btn-outline"
            onClick={handleLogout}
          >
            <LogOut size={18} />
            로그아웃
          </button>
        </div>
      </div>
    </div>
  );
}
