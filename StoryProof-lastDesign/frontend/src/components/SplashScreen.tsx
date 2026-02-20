import { useEffect, useState } from 'react';
import { BookOpen } from 'lucide-react';

interface SplashScreenProps {
    /** 커스텀 스플래시 이미지 URL 배열 (5개 중 랜덤 선택) */
    imageUrls?: string[];
    /** 로딩 메시지 */
    message?: string;
}

/**
 * 스플래시/로딩 화면 컴포넌트
 * 서버 모델 로딩 중에 표시됩니다.
 * imageUrls 배열에서 랜덤하게 하나를 선택하여 전체 화면에 표시합니다.
 */
export function SplashScreen({
    imageUrls = [],
    message = 'AI 모델을 불러오는 중입니다...'
}: SplashScreenProps) {
    const [dots, setDots] = useState('');
    const [fadeIn, setFadeIn] = useState(false);
    const [selectedImage, setSelectedImage] = useState<string | null>(null);

    // 랜덤 이미지 선택 (마운트 시 한 번만)
    useEffect(() => {
        if (imageUrls.length > 0) {
            const randomIndex = Math.floor(Math.random() * imageUrls.length);
            const selected = imageUrls[randomIndex];
            console.log(`[SplashScreen] Received ${imageUrls.length} images, selected:`, selected);
            setSelectedImage(selected);
        } else {
            console.log('[SplashScreen] No images available, using default logo');
        }
    }, [imageUrls]);

    // 로딩 dots 애니메이션
    useEffect(() => {
        const interval = setInterval(() => {
            setDots(prev => prev.length >= 3 ? '' : prev + '.');
        }, 500);
        return () => clearInterval(interval);
    }, []);

    // 초기 페이드인
    useEffect(() => {
        const timer = setTimeout(() => setFadeIn(true), 100);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div className={`splash-container ${fadeIn ? 'splash-visible' : ''}`}>
            {/* 배경 그라데이션 오버레이 */}
            <div className="splash-bg-overlay" />

            {/* 전체 화면 이미지 (있을 경우) */}
            {selectedImage && (
                <div className="splash-fullscreen-image-wrapper">
                    <img
                        src={selectedImage}
                        alt="StoryProof"
                        className="splash-fullscreen-image"
                    />
                    <div className="splash-image-overlay" />
                </div>
            )}

            {/* 기본 로고 (이미지 없을 때만) */}
            {!selectedImage && (
                <div className="splash-default-logo-center">
                    <div className="splash-logo-glow" />
                    <BookOpen size={80} strokeWidth={1.5} className="splash-logo-icon" />
                </div>
            )}

            {/* 하단 콘텐츠 (브랜드명, 프로그레스, 메시지) */}
            <div className="splash-bottom-content">
                {/* 브랜드 이름 */}
                <h1 className="splash-brand">StoryProof</h1>
                <p className="splash-tagline">소설 분석 및 피드백 플랫폼</p>

                {/* 프로그레스 바 */}
                <div className="splash-progress-container">
                    <div className="splash-progress-bar">
                        <div className="splash-progress-fill" />
                    </div>
                </div>

                {/* 로딩 메시지 */}
                <p className="splash-message">{message}{dots}</p>
            </div>
        </div>
    );
}
