import { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, User, BookOpen } from 'lucide-react';
import { ChapterDetail } from './components/ChapterDetail';
import { FileUpload } from './components/FileUpload';
import { ThemeToggle } from './components/ThemeToggle';
// import { ChatBot } from './components/ChatBot';
import { register, login } from './api/auth';
import { getNovels, createNovel, Novel } from './api/novel';

type Screen = 'login' | 'signup' | 'upload' | 'chapterDetail';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [selectedChapterId, setSelectedChapterId] = useState<number | undefined>(undefined);
  const [currentNovel, setCurrentNovel] = useState<Novel | null>(null);
  const [userMode, setUserMode] = useState<'reader' | 'writer'>(
    (localStorage.getItem('userMode') as 'reader' | 'writer') || 'writer'
  );

  // Login/Signup form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [signupMode, setSignupMode] = useState<'reader' | 'writer'>('writer');

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Login attempt:', { email, rememberMe });

    try {
      // 1. Login
      const tokenResponse = await login({ email, password });
      localStorage.setItem('token', tokenResponse.access_token);
      localStorage.setItem('userMode', tokenResponse.mode);
      setUserMode(tokenResponse.mode);

      // 2. Fetch or Create Novel
      try {
        const novelsResponse = await getNovels();
        if (novelsResponse.novels.length > 0) {
          setCurrentNovel(novelsResponse.novels[0]);
        } else {
          const newNovel = await createNovel({
            title: "My First Novel",
            description: "Default created novel",
            genre: "General"
          });
          setCurrentNovel(newNovel);
        }
      } catch (error) {
        console.error("Failed to fetch novels:", error);
        alert("로그인은 성공했으나 소설 정보를 가져오는데 실패했습니다.");
      }

      setCurrentScreen('upload');
    } catch (error) {
      console.error("Login failed:", error);
      alert("로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.");
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      alert('비밀번호가 일치하지 않습니다.');
      return;
    }
    if (!agreeToTerms) {
      alert('이용약관 및 개인정보 처리방침에 동의해주세요.');
      return;
    }

    try {
      await register({
        username: name,
        email: email,
        password: password,
        mode: signupMode
      });
      alert('회원가입이 완료되었습니다. 로그인해주세요.');
      setCurrentScreen('login');
      // Reset form
      setName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setAgreeToTerms(false);
    } catch (error) {
      if (error instanceof Error) {
        alert(`회원가입 실패: ${error.message}`);
      } else {
        alert('회원가입 중 오류가 발생했습니다.');
      }
      console.error('Signup failed:', error);
    }
  };

  // Upload Screen
  if (currentScreen === 'upload') {
    return (
      <FileUpload
        onFileClick={(chapter) => {
          console.log("Chapter selected:", chapter);
          setSelectedFile(chapter.title);
          setSelectedChapterId(chapter.id);
          setCurrentScreen('chapterDetail');
        }}
        novelId={currentNovel?.id}
        mode={userMode}
      />
    );
  }

  // Chapter Detail Screen
  if (currentScreen === 'chapterDetail') {
    return (
      <ChapterDetail
        fileName={selectedFile}
        onBack={() => setCurrentScreen('upload')}
        novelId={currentNovel?.id}
        chapterId={selectedChapterId}
        mode={userMode}
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

              {/* Mode Selection */}
              <div className="form-group">
                <label className="form-label">모드 선택</label>
                <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setSignupMode('writer')}
                    className={`mode-toggle-btn ${signupMode === 'writer' ? 'active' : ''}`}
                    style={{
                      flex: 1,
                      padding: '10px',
                      borderRadius: '8px',
                      border: signupMode === 'writer' ? '2px solid #4F46E5' : '1px solid #E5E7EB',
                      backgroundColor: signupMode === 'writer' ? '#EEF2FF' : 'white',
                      color: signupMode === 'writer' ? '#4F46E5' : '#6B7280',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    작가 모드
                  </button>
                  <button
                    type="button"
                    onClick={() => setSignupMode('reader')}
                    className={`mode-toggle-btn ${signupMode === 'reader' ? 'active' : ''}`}
                    style={{
                      flex: 1,
                      padding: '10px',
                      borderRadius: '8px',
                      border: signupMode === 'reader' ? '2px solid #4F46E5' : '1px solid #E5E7EB',
                      backgroundColor: signupMode === 'reader' ? '#EEF2FF' : 'white',
                      color: signupMode === 'reader' ? '#4F46E5' : '#6B7280',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    독자 모드
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
