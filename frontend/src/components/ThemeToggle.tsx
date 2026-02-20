import { Sun, Moon, Coffee } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();

    const getIcon = () => {
        if (theme === 'light') return <Sun size={24} />;
        if (theme === 'sepia') return <Coffee size={24} style={{ color: '#6b4f3a' }} />;
        return <Moon size={24} />;
    };

    const getTitle = () => {
        if (theme === 'light') return '화이트 모드 (클릭 시 세피아)';
        if (theme === 'sepia') return '세피아 모드 (클릭 시 다크)';
        return '다크 모드 (클릭 시 화이트)';
    };

    return (
        <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={getTitle()}
            style={theme === 'sepia' ? { backgroundColor: '#ede0d4' } : undefined}
        >
            {getIcon()}
        </button>
    );
}
