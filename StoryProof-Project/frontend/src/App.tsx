import { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, User, BookOpen } from 'lucide-react';
import { ChapterDetail } from './components/ChapterDetail';
import { FileUpload } from './components/FileUpload';
import { ThemeToggle } from './components/ThemeToggle';
import { ChatBot } from './components/ChatBot';

type Screen = 'login' | 'signup' | 'upload' | 'chapterDetail';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [selectedFile, setSelectedFile] = useState<string>('');

  // Login/Signup form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Login attempt:', { email, rememberMe });
    // Navigate to upload screen
    setCurrentScreen('upload');
  };

  const handleSignupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      alert('비밀번호가 일치하지 않습니다.');
      return;
    }
    if (!agreeToTerms) {
      alert('이용약관 및 개인정보 처리방침에 동의해주세요.');
      return;
    }
    console.log('Signup attempt:', { name, email, agreeToTerms });
  };

  // Upload Screen
  if (currentScreen === 'upload') {
    return (
      <FileUpload
        onFileClick={(fileName) => {
          setSelectedFile(fileName);
          setCurrentScreen('chapterDetail');
        }}
      />
    );
  }

  // Chapter Detail Screen
  if (currentScreen === 'chapterDetail') {
    return (
      <ChapterDetail
        fileName={selectedFile}
        onBack={() => setCurrentScreen('upload')}
      />
    );
  }

  if (currentScreen === 'signup') {
    return (
      <div className="login-container">
        <div className="login-card">
          {/* Logo and Brand */}
          <div className="brand-header">
            <div className="logo-icon">
              <BookOpen size={32} strokeWidth={2.5} />
            </div>
            <h1 className="brand-name">StoryProof</h1>
          </div>

          {/* Signup Form */}
          <div className="login-form-wrapper">
            <h2 className="login-title">회원가입</h2>
            <p className="login-subtitle">새 계정을 만들어 시작하세요</p>

            <form onSubmit={handleSignupSubmit} className="login-form">
              {/* Name Input */}
              <div className="form-group">
                <label htmlFor="name" className="form-label">
                  이름
                </label>
                <div className="input-wrapper">
                  <User className="input-icon" size={20} />
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="홍길동"
                    className="form-input"
                    required
                  />
                </div>
              </div>

              {/* Email Input */}
              <div className="form-group">
                <label htmlFor="signup-email" className="form-label">
                  이메일
                </label>
                <div className="input-wrapper">
                  <Mail className="input-icon" size={20} />
                  <input
                    id="signup-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="form-input"
                    required
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="form-group">
                <label htmlFor="signup-password" className="form-label">
                  비밀번호
                </label>
                <div className="input-wrapper">
                  <Lock className="input-icon" size={20} />
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="········"
                    className="form-input"
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="password-toggle"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              {/* Confirm Password Input */}
              <div className="form-group">
                <label htmlFor="confirm-password" className="form-label">
                  비밀번호 확인
                </label>
                <div className="input-wrapper">
                  <Lock className="input-icon" size={20} />
                  <input
                    id="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="········"
                    className="form-input"
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="password-toggle"
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              {/* Terms Agreement */}
              <div className="form-options" style={{ justifyContent: 'flex-start' }}>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={agreeToTerms}
                    onChange={(e) => setAgreeToTerms(e.target.checked)}
                    className="checkbox-input"
                    required
                  />
                  <span className="checkbox-text">
                    <a href="#" className="inline-link">이용약관</a> 및{' '}
                    <a href="#" className="inline-link">개인정보 처리방침</a>에 동의합니다
                  </span>
                </label>
              </div>

              {/* Signup Button */}
              <button type="submit" className="login-button">
                회원가입
              </button>
            </form>

            {/* Login Link */}
            <p className="signup-text">
              이미 계정이 있으신가요?{' '}
              <button
                onClick={() => setCurrentScreen('login')}
                className="signup-link"
                style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
              >
                로그인
              </button>
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Login Screen
  return (
    <div className="login-container">
      <div className="login-card">
        {/* Logo and Brand */}
        <div className="brand-header">
          <div className="logo-icon">
            <BookOpen size={32} strokeWidth={2.5} />
          </div>
          <h1 className="brand-name">StoryProof</h1>
        </div>

        {/* Login Form */}
        <div className="login-form-wrapper">
          <h2 className="login-title">로그인</h2>
          <p className="login-subtitle">계정에 로그인하여 계속하세요</p>

          <form onSubmit={handleLoginSubmit} className="login-form">
            {/* Email Input */}
            <div className="form-group">
              <label htmlFor="email" className="form-label">
                이메일
              </label>
              <div className="input-wrapper">
                <Mail className="input-icon" size={20} />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="form-input"
                  required
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="form-group">
              <label htmlFor="password" className="form-label">
                비밀번호
              </label>
              <div className="input-wrapper">
                <Lock className="input-icon" size={20} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="········"
                  className="form-input"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="password-toggle"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* Remember Me & Forgot Password */}
            <div className="form-options">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="checkbox-input"
                />
                <span className="checkbox-text">로그인 상태 유지</span>
              </label>
              <a href="#" className="forgot-password">
                비밀번호 찾기
              </a>
            </div>

            {/* Login Button */}
            <button type="submit" className="login-button">
              로그인
            </button>
          </form>

          {/* Sign Up Link */}
          <p className="signup-text">
            아직 계정이 없으신가요?{' '}
            <button
              onClick={() => setCurrentScreen('signup')}
              className="signup-link"
              style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
            >
              회원가입
            </button>
          </p>
        </div>
      </div>

      {/* Global Components */}
      <ThemeToggle />
    </div>
  );
}
