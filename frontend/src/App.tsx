import { useState, useEffect, lazy, Suspense } from 'react';
import { toast } from 'sonner';
import { Mail, Lock, Eye, EyeOff, User, ArrowLeft } from 'lucide-react';
import logoImg from './assets/logo.png';
import splashImg1 from './assets/KakaoTalk_20260219_151600086_01.png';
import splashImg2 from './assets/KakaoTalk_20260219_151600086_02.png';
import splashImg3 from './assets/KakaoTalk_20260219_151600086_03.png';
import splashImg4 from './assets/KakaoTalk_20260219_151600086_04.png';
import splashImg5 from './assets/KakaoTalk_20260219_151600086.png';
import { ThemeToggle } from './components/ThemeToggle';
import { register, login } from './api/auth';
import { getNovels, createNovel, Novel } from './api/novel';
import { SplashScreen } from './components/SplashScreen';

// Lazy-loaded 화면 컴포넌트 (코드 스플리팅)
const ChapterDetail = lazy(() => import('./components/ChapterDetail').then(m => ({ default: m.ChapterDetail })));
const FileUpload = lazy(() => import('./components/FileUpload').then(m => ({ default: m.FileUpload })));
const CharacterChatBot = lazy(() => import('./components/CharacterChatBot').then(m => ({ default: m.CharacterChatBot })));
const LandingPage = lazy(() => import('./components/LandingPage').then(m => ({ default: m.LandingPage })));

const SPLASH_IMAGES = [splashImg1, splashImg2, splashImg3, splashImg4, splashImg5];

type Screen = 'landing' | 'login' | 'signup' | 'upload' | 'chapterDetail';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('landing');
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [selectedChapterId, setSelectedChapterId] = useState<number | undefined>(undefined);
  const [currentNovel, setCurrentNovel] = useState<Novel | null>(null);
  const [showChatBot, setShowChatBot] = useState(false);

  // 서버 준비 상태 (AI 모델 로딩)
  const [isServerReady, setIsServerReady] = useState(false);
  const [splashFadeOut, setSplashFadeOut] = useState(false);

  // 서버 readiness 폴링
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval>;
    let mounted = true;

    const checkReady = async () => {
      try {
        const res = await fetch('/api/v1/health/ready');
        if (res.ok && mounted) {
          const data = await res.json();
          if (data.ready) {
            setSplashFadeOut(true);
            setTimeout(() => {
              if (mounted) setIsServerReady(true);
            }, 700);
            clearInterval(intervalId);
          }
        }
      } catch {
        // 서버 아직 미시작 - 계속 폴링
      }
    };

    checkReady();
    intervalId = setInterval(checkReady, 2000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  // Login/Signup form states
  const [userMode, setUserMode] = useState<'reader' | 'writer'>(
    (localStorage.getItem('userMode') as 'reader' | 'writer') || 'writer'
  );
  const [signupMode, setSignupMode] = useState<'reader' | 'writer'>('writer');

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

    try {
      const tokenResponse = await login({ email, password });
      localStorage.setItem('token', tokenResponse.access_token);
      localStorage.setItem('userMode', tokenResponse.user_mode);
      setUserMode(tokenResponse.user_mode);

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
        toast.error("로그인은 성공했으나 소설 정보를 가져오는데 실패했습니다.");
      }

      setCurrentScreen('upload');
    } catch (error) {
      console.error("Login failed:", error);
      toast.error("로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.");
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      toast.error('비밀번호가 일치하지 않습니다.');
      return;
    }
    if (!agreeToTerms) {
      toast.error('이용약관 및 개인정보 처리방침에 동의해주세요.');
      return;
    }

    try {
      await register({
        username: name,
        email: email,
        password: password,
        user_mode: signupMode
      });
      toast.success('회원가입이 완료되었습니다. 로그인해주세요.');
      setCurrentScreen('login');
      setName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      setAgreeToTerms(false);
    } catch (error) {
      if (error instanceof Error) {
        toast.error(`회원가입 실패: ${error.message}`);
      } else {
        toast.error('회원가입 중 오류가 발생했습니다.');
      }
      console.error('Signup failed:', error);
    }
  };

  // 스플래시 화면 (서버 모델 로딩 중)
  if (!isServerReady) {
    return (
      <div className={splashFadeOut ? 'splash-fade-out' : ''}>
        <SplashScreen
          imageUrls={SPLASH_IMAGES}
          message="AI 모델을 불러오는 중입니다"
        />
      </div>
    );
  }

  // Landing Screen
  if (currentScreen === 'landing') {
    return (
      <Suspense fallback={
        <div className="skeleton-loader">
          <div className="skeleton-bar skeleton-wide" />
          <div className="skeleton-bar skeleton-narrow" />
        </div>
      }>
        <LandingPage
          onLogin={() => setCurrentScreen('login')}
          onSignup={() => setCurrentScreen('signup')}
        />
      </Suspense>
    );
  }

  // Upload Screen
  if (currentScreen === 'upload') {
    return (
      <Suspense fallback={
        <div className="skeleton-loader">
          <div className="skeleton-bar skeleton-wide" />
          <div className="skeleton-bar skeleton-narrow" />
        </div>
      }>
        <FileUpload
          onFileClick={(chapter) => {
            setSelectedFile(chapter.title);
            setSelectedChapterId(chapter.id);
            setCurrentScreen('chapterDetail');
          }}
          novelId={currentNovel?.id}
          mode={userMode}
        />
      </Suspense>
    );
  }

  // Chapter Detail Screen
  if (currentScreen === 'chapterDetail') {
    return (
      <Suspense fallback={
        <div className="skeleton-loader">
          <div className="skeleton-bar skeleton-wide" />
          <div className="skeleton-bar skeleton-narrow" />
        </div>
      }>
        <ChapterDetail
          fileName={selectedFile}
          onBack={() => setCurrentScreen('upload')}
          novelId={currentNovel?.id}
          chapterId={selectedChapterId}
          mode={userMode}
          onOpenCharacterChat={() => setShowChatBot(true)}
          onCloseCharacterChat={() => setShowChatBot(false)}
          showCharacterChat={showChatBot}
          onNavigateChapter={(newChapterId, newTitle) => {
            setSelectedChapterId(newChapterId);
            setSelectedFile(newTitle);
          }}
        />
        {currentNovel && showChatBot && (
          <CharacterChatBot
            novelId={currentNovel.id}
            chapterId={selectedChapterId}
            onClose={() => setShowChatBot(false)}
          />
        )}
      </Suspense>
    );
  }

  if (currentScreen === 'signup') {
    return (
      <div className="login-container">
        <div className="login-card">
          <button
            onClick={() => setCurrentScreen('landing')}
            style={{
              position: 'absolute', top: '16px', left: '16px',
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#78716c', padding: '6px', borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = '#1c1917'}
            onMouseLeave={(e) => e.currentTarget.style.color = '#78716c'}
            title="첫 화면으로"
          >
            <ArrowLeft size={20} />
          </button>
          {/* Logo and Brand */}
          <div className="brand-header">
            <div className="logo-icon">
              <img src={logoImg} alt="StoryProof Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            </div>
            <h1 className="brand-name">StoryProof</h1>
          </div>

          {/* Signup Form */}
          <div className="login-form-wrapper">
            <h2 className="login-title">회원가입</h2>
            <p className="login-subtitle">새 계정을 만들어 시작하세요</p>

            <form onSubmit={handleSignupSubmit} className="login-form">
              {/* Mode Selection */}
              <div className="form-group">
                <label className="form-label">사용자 모드</label>
                <div style={{ display: 'flex', gap: '12px' }}>
                  <button
                    type="button"
                    onClick={() => setSignupMode('writer')}
                    className="mode-button"
                    style={{
                      flex: 1,
                      padding: '10px',
                      borderRadius: '8px',
                      border: `1px solid ${signupMode === 'writer' ? '#4F46E5' : '#E5E7EB'}`,
                      backgroundColor: signupMode === 'writer' ? '#EEF2FF' : 'white',
                      color: signupMode === 'writer' ? '#4F46E5' : '#374151',
                      cursor: 'pointer',
                      fontWeight: 500
                    }}
                  >
                    ✍️ 작가 모드
                  </button>
                  <button
                    type="button"
                    onClick={() => setSignupMode('reader')}
                    className="mode-button"
                    style={{
                      flex: 1,
                      padding: '10px',
                      borderRadius: '8px',
                      border: `1px solid ${signupMode === 'reader' ? '#0284C7' : '#E5E7EB'}`,
                      backgroundColor: signupMode === 'reader' ? '#E0F2FE' : 'white',
                      color: signupMode === 'reader' ? '#0284C7' : '#374151',
                      cursor: 'pointer',
                      fontWeight: 500
                    }}
                  >
                    📖 독자 모드
                  </button>
                </div>
              </div>

              {/* Name Input */}
              <div className="form-group">
                <label htmlFor="name" className="form-label">이름</label>
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
                <label htmlFor="signup-email" className="form-label">이메일</label>
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
                <label htmlFor="signup-password" className="form-label">비밀번호</label>
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
                <label htmlFor="confirm-password" className="form-label">비밀번호 확인</label>
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
        <button
          onClick={() => setCurrentScreen('landing')}
          style={{
            position: 'absolute', top: '16px', left: '16px',
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#78716c', padding: '6px', borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'color 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = '#1c1917'}
          onMouseLeave={(e) => e.currentTarget.style.color = '#78716c'}
          title="첫 화면으로"
        >
          <ArrowLeft size={20} />
        </button>
        {/* Logo and Brand */}
        <div className="brand-header">
          <div className="logo-icon">
            <img src={logoImg} alt="StoryProof Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
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

            {/* Password Input */}
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
