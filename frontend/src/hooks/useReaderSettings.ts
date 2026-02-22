import { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';

export interface ReaderSettings {
    fontSize: number;
    lineHeight: number;
    paragraphSpacing: number;
    contentWidth: number;
    fontFamily: string;
    theme: string;
}

const DEFAULT_READER_SETTINGS: ReaderSettings = {
    fontSize: 18,
    lineHeight: 2.0,
    paragraphSpacing: 40,
    contentWidth: 80,
    fontFamily: 'Noto Serif KR',
    theme: 'light',
};

export function useReaderSettings(mode: 'reader' | 'writer'): {
    readerSettings: ReaderSettings;
    handleReaderSettingsChange: (newSettings: ReaderSettings) => void;
} {
    const { theme: globalTheme, setTheme: setGlobalTheme } = useTheme();

    // Reader Mode Settings (initialized from localStorage)
    const [readerSettings, setReaderSettings] = useState<ReaderSettings>(() => {
        const saved = localStorage.getItem('reader-settings');
        return saved ? JSON.parse(saved) : DEFAULT_READER_SETTINGS;
    });

    // 1. Sync globalTheme -> readerSettings.theme (when global toggle is clicked)
    useEffect(() => {
        if (mode === 'reader' && readerSettings.theme !== globalTheme) {
            setReaderSettings((prev) => ({ ...prev, theme: globalTheme }));
        }
    }, [globalTheme, mode]);

    // Handler for reader toolbar settings changes
    const handleReaderSettingsChange = (newSettings: ReaderSettings) => {
        setReaderSettings(newSettings);
        // 2. Sync readerSettings.theme -> globalTheme (when reader toolbar setting is changed)
        if (newSettings.theme && newSettings.theme !== globalTheme) {
            setGlobalTheme(newSettings.theme as 'light' | 'sepia' | 'dark');
        }
    };

    // Persist to localStorage + apply document attributes in reader mode
    useEffect(() => {
        localStorage.setItem('reader-settings', JSON.stringify(readerSettings));

        // Apply theme to document for reader mode
        if (mode === 'reader') {
            document.documentElement.setAttribute('data-reader-theme', readerSettings.theme);
            document.documentElement.setAttribute('data-theme', readerSettings.theme);
        } else {
            document.documentElement.removeAttribute('data-reader-theme');
            // Restore global theme if needed, but ThemeContext handles that
        }
    }, [readerSettings, mode]);

    return {
        readerSettings,
        handleReaderSettingsChange,
    };
}
