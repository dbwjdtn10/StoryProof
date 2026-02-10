import { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, User, BookOpen } from 'lucide-react';
import { ChapterDetail } from './components/ChapterDetail';
import { FileUpload } from './components/FileUpload';
import { ThemeToggle } from './components/ThemeToggle';
import { Toaster } from './components/ui/sonner';
// import { ChatBot } from './components/ChatBot';
import { register, login } from './api/auth';
import { getNovels, createNovel, Novel } from './api/novel';

type Screen = 'login' | 'signup' | 'upload' | 'chapterDetail';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [selectedChapterId, setSelectedChapterId] = useState<number | undefined>(undefined);
  const [currentNovel, setCurrentNovel] = useState<Novel | null>(null);

  // Login/Signup form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [agreeToTerms, setAgreeToTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Login attempt:', { email, rememberMe });

    try {
      // 1. Login
      const tokenResponse = await login({ email, password });
      localStorage.setItem('token', tokenResponse.access_token);

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
        password: password
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
    <div className="login-container" style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>

      {/* --- 창 밖 최상단에 배치되는 홍보 문구 --- */}
      <div style={{
        position: 'absolute',
        top: '5%', // 화면 상단에서 15% 지점에 고정
        left: '50%',
        transform: 'translateX(-50%)', // 가로 중앙 정렬 보정
        textAlign: 'center',
        fontSize: '2.0rem',
        fontWeight: '900', // 1000은 지원되지 않는 경우가 많아 900(Heavy) 추천
        color: '#4F46E5',
        textShadow: '0px 2px 4px rgba(0,0,0,0.1)',
        zIndex: 1,
        whiteSpace: 'nowrap' // 문장이 한 줄로 나오도록 고정
      }}>
        "설정 파괴까지 잡아내는 AI 서사 분석"
      </div>

      <div className="login-card" style={{ marginTop: '100px' }}> {/* 문구와의 간격을 위해 여백 추가 */}
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
            {/* 이메일 입력 (기존과 동일) */}
            <div className="form-group">
              <label htmlFor="email" className="form-label">이메일</label>
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

            {/* 비밀번호 입력 (기존과 동일) */}
            <div className="form-group">
              <label htmlFor="password" className="form-label">비밀번호</label>
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
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {/* 옵션 및 로그인 버튼 (기존과 동일) */}
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
              <a href="#" className="forgot-password">비밀번호 찾기</a>
            </div>

            <button type="submit" className="login-button">로그인</button>
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

          {/* --- 가이드라인 섹션 추가 시작 --- */}
          <div className="guide-section" style={{ marginTop: '32px', borderTop: '1px solid #eee', paddingTop: '24px' }}>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontWeight: 'bold', color: '#4F46E5', fontSize: '0.9rem', marginBottom: '4px' }}>Story borad</div>
              <p style={{ color: '#666', fontSize: '0.85rem', margin: 0 }}>"인물과 아이템을 자동으로 정리하는 똑똑한 사전"</p>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontWeight: 'bold', color: '#4F46E5', fontSize: '0.9rem', marginBottom: '4px' }}>설정 파괴 탐지</div>
              <p style={{ color: '#666', fontSize: '0.85rem', margin: 0 }}>"개연성을 지켜주는 AI 편집자의 실시간 피드백"</p>
            </div>
            <div>
              <div style={{ fontWeight: 'bold', color: '#4F46E5', fontSize: '0.9rem', marginBottom: '4px' }}>전용 챗봇</div>
              <p style={{ color: '#666', fontSize: '0.85rem', margin: 0 }}>"소설의 모든 것을 기억하고 답하는 챗봇"</p>
            </div>
          </div>
          {/* --- 가이드라인 섹션 추가 끝 --- */}

        </div>
      </div>

      <ThemeToggle />
      <Toaster richColors position="top-right" />
    </div>
  );
}
