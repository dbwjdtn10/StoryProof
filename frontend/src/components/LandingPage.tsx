import { useState, useEffect, useRef, useCallback } from 'react';
import { BookOpen, ShieldAlert, FileQuestion, GitFork, MessageSquareMore } from 'lucide-react';
import './LandingPage.css';

// 슬라이드 이미지 경로 (실제 경로에 맞게 수정 필요)
const SLIDE_IMAGES = [
    '/static/images/slides/slide1.png',
    '/static/images/slides/slide2.png',
    '/static/images/slides/slide3.png',
    '/static/images/slides/slide4.png',
    '/static/images/slides/slide5.png',
];
const FALLBACK_IMAGE = '/static/images/slides/default.png';
const SLIDE_INTERVAL = 4500;

// 상단 기능 카드 데이터 (아이콘, 제목, 설명, 태그)
const TOP_FEATURES = [
    {
        icon: <BookOpen size={36} strokeWidth={1.5} />,
        title: '자동 설정집',
        desc: '당신의 소설 속 인물과 장소, 사건 등을 빠르게 읽고 찾을 수 있도록 정리해줍니다.',
        tags: ['#해당_장면까지', '#자동_스크롤'],
    },
    {
        icon: <ShieldAlert size={36} strokeWidth={1.5} />,
        title: '설정 파괴 탐지기',
        desc: '소설을 분석하여 설정 충돌이나 개연성 경고를 찾아내고 대안을 제시합니다.',
        tags: ['#독자보다_먼저', '#탄탄한_스토리'],
    },
];

// 하단 기능 카드 데이터 (설명 제외)
const BOTTOM_FEATURES = [
    {
        icon: <FileQuestion size={36} strokeWidth={1.5} />,
        title: '스토리 Q&A',
        tags: ['#소설_내용_검색', '#뭐든지_질문'],
    },
    {
        icon: <GitFork size={36} strokeWidth={1.5} className="rotate-90" />, // 아이콘 회전
        title: '스토리 예측',
        tags: ['#What-if', '#시뮬레이션'],
    },
    {
        icon: <MessageSquareMore size={36} strokeWidth={1.5} />,
        title: '캐릭터 챗봇',
        tags: ['#소설_인물과_직접', '#인터뷰'],
    },
];

// 스크롤 애니메이션을 위한 전체 기능 리스트
const ALL_FEATURES = [...TOP_FEATURES, ...BOTTOM_FEATURES];

interface LandingPageProps {
    onLogin: () => void;
    onSignup: () => void;
}

export function LandingPage({ onLogin, onSignup }: LandingPageProps) {
    const [currentSlide, setCurrentSlide] = useState(0);
    const [imgErrors, setImgErrors] = useState<boolean[]>(Array(SLIDE_IMAGES.length).fill(false));
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const featureRefs = useRef<(HTMLDivElement | null)[]>([]);
    const [visibleFeatures, setVisibleFeatures] = useState<boolean[]>(Array(ALL_FEATURES.length).fill(false));

    // 자동 슬라이드 타이머 설정
    const startTimer = useCallback(() => {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = setInterval(() => {
            setCurrentSlide((prev) => (prev + 1) % SLIDE_IMAGES.length);
        }, SLIDE_INTERVAL);
    }, []);

    useEffect(() => {
        startTimer();
        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, [startTimer]);

    const goToSlide = (index: number) => {
        setCurrentSlide(index);
        startTimer();
    };

    const handleImgError = (index: number) => {
        setImgErrors((prev) => {
            const next = [...prev];
            next[index] = true;
            return next;
        });
    };

    // 스크롤 시 기능 카드 페이드인 애니메이션
    useEffect(() => {
        const observers: IntersectionObserver[] = [];
        featureRefs.current.forEach((el, i) => {
            if (!el) return;
            const obs = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        if (entry.isIntersecting) {
                            // 순차적으로 나타나도록 딜레이 적용
                            setTimeout(() => {
                                setVisibleFeatures((prev) => {
                                    const next = [...prev];
                                    next[i] = true;
                                    return next;
                                });
                            }, i * 150);
                            obs.disconnect();
                        }
                    });
                },
                { threshold: 0.2 }
            );
            obs.observe(el);
            observers.push(obs);
        });
        return () => observers.forEach((o) => o.disconnect());
    }, []);

    return (
        <div className="landing-root">
            {/* 헤더: 우측 상단 로그인/회원가입 링크 */}
            <header className="landing-header">
                <nav className="landing-nav-links">
                    <button className="landing-link-btn" onClick={onSignup}>회원가입</button>
                    <span className="landing-link-separator">|</span>
                    <button className="landing-link-btn" onClick={onLogin}>로그인</button>
                </nav>
            </header>

            <main className="landing-main">
                {/* 히어로 섹션: 중앙 로고 및 슬라이더 */}
                <section className="landing-hero">
                    <h1 className="landing-main-logo">StoryProof</h1>
                    <div className="landing-slider-container">
                        <div
                            className="landing-slider"
                            style={{ transform: `translateX(-${currentSlide * 100}%)` }}
                        >
                            {SLIDE_IMAGES.map((src, i) => (
                                <div
                                    key={i}
                                    className="landing-slide"
                                    aria-hidden={i !== currentSlide}
                                >
                                    {imgErrors[i] ? (
                                        <div className="landing-slide-fallback">
                                            <img src={FALLBACK_IMAGE} alt="기본 이미지" className="landing-slide-fallback-img" />
                                        </div>
                                    ) : (
                                        <img src={src} alt={`슬라이드 ${i + 1}`} className="landing-slide-img" onError={() => handleImgError(i)} />
                                    )}
                                </div>
                            ))}
                        </div>
                        {/* 슬라이드 인디케이터 */}
                        <div className="landing-indicators">
                            {SLIDE_IMAGES.map((_, i) => (
                                <button
                                    key={i}
                                    className={`landing-indicator-dot ${i === currentSlide ? 'active' : ''}`}
                                    onClick={() => goToSlide(i)}
                                    aria-label={`${i + 1}번 슬라이드로 이동`}
                                />
                            ))}
                        </div>
                    </div>
                </section>

                {/* 기능 소개 섹션: 상단/하단 2행 구조 */}
                <section className="landing-features">
                    <div className="landing-features-inner">
                        {/* 상단 행 (투명 배경 카드) */}
                        <div className="landing-features-row top">
                            {TOP_FEATURES.map((f, i) => (
                                <div
                                    key={i}
                                    ref={(el) => { featureRefs.current[i] = el; }}
                                    className={`landing-feature-card top-card ${visibleFeatures[i] ? 'visible' : ''}`}
                                >
                                    <div className="landing-feature-icon-wrapper">{f.icon}</div>
                                    <div className="landing-feature-content">
                                        <h3 className="landing-feature-title">{f.title}</h3>
                                        <p className="landing-feature-desc">{f.desc}</p>
                                        <div className="landing-feature-tags">
                                            {f.tags.map((tag, ti) => (
                                                <span key={ti} className="landing-feature-tag">{tag}</span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                        {/* 하단 행 (어두운 배경 카드) */}
                        <div className="landing-features-row bottom">
                            {BOTTOM_FEATURES.map((f, i) => {
                                const globalIndex = TOP_FEATURES.length + i;
                                return (
                                    <div
                                        key={globalIndex}
                                        ref={(el) => { featureRefs.current[globalIndex] = el; }}
                                        className={`landing-feature-card bottom-card ${visibleFeatures[globalIndex] ? 'visible' : ''}`}
                                    >
                                        <div className="landing-feature-icon-wrapper">{f.icon}</div>
                                        <h3 className="landing-feature-title">{f.title}</h3>
                                        <div className="landing-feature-tags">
                                            {f.tags.map((tag, ti) => (
                                                <span key={ti} className="landing-feature-tag">{tag}</span>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}