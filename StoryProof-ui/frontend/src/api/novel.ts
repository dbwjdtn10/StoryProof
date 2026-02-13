
import { request } from './client';

export interface Novel {
    id: number;
    title: string;
    description: string;
    genre: string;
    author_id: number;
    is_public: boolean;
    is_completed: boolean;
    created_at: string;
    chapter_count?: number;
}

export interface NovelListResponse {
    total: number;
    novels: Novel[];
}

export interface Chapter {
    id: number;
    novel_id: number;
    chapter_number: number;
    title: string;
    content: string;
    word_count: number;
    created_at: string;
    storyboard_status?: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    storyboard_progress?: number;
    storyboard_message?: string;
}

export interface StoryboardProgress {
    chapter_id: number;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    message?: string;
    error?: string;
}

const getHeaders = (): Record<string, string> => {
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

export const getNovels = async (skip = 0, limit = 10): Promise<NovelListResponse> => {
    return request<NovelListResponse>(`/novels/?skip=${skip}&limit=${limit}`, {
        method: 'GET',
        headers: getHeaders(),
    });
};

export const createNovel = async (data: { title: string; description?: string; genre?: string; is_public?: boolean }) => {
    return request<Novel>('/novels/', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
};

export const getChapters = async (novelId: number): Promise<Chapter[]> => {
    try {
        const chapters = await request<Chapter[]>(`/novels/${novelId}/chapters`, {
            method: 'GET',
            headers: getHeaders(),
        });
        return chapters;
    } catch (error) {
        throw error;
    }
};

export const uploadChapter = async (
    novelId: number,
    file: File,
    chapterNumber: number,
    title: string
): Promise<Chapter> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('chapter_number', chapterNumber.toString());
    formData.append('title', title);

    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    // Note: Content-Type for FormData is automatically set by browser

    const response = await fetch(`http://localhost:8000/api/v1/novels/${novelId}/chapters/upload`, {
        method: 'POST',
        headers: headers,
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to upload chapter');
    }

    const uploadedChapter = await response.json();
    return uploadedChapter;
};

export const getChapter = async (novelId: number, chapterId: number): Promise<Chapter> => {
    if (!novelId || !chapterId) {
        throw new Error(`Missing required parameters: novelId=${novelId}, chapterId=${chapterId}`);
    }

    const endpoint = `/novels/${novelId}/chapters/${chapterId}`;
    const headers = getHeaders();

    try {
        const chapter = await request<Chapter>(endpoint, {
            method: 'GET',
            headers: headers,
        });
        return chapter;
    } catch (error) {
        throw error;
    }
};

export const updateChapter = async (novelId: number, chapterId: number, data: { title?: string; content?: string; scenes?: string[] }) => {
    return request<Chapter>(`/novels/${novelId}/chapters/${chapterId}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
};

export const deleteChapter = async (novelId: number, chapterId: number): Promise<void> => {
    try {
        const response = await request<void>(`/novels/${novelId}/chapters/${chapterId}`, {
            method: 'DELETE',
            headers: getHeaders(),
        });
        return response;
    } catch (error) {
        throw error;
    }
};

export const getStoryboardStatus = async (novelId: number, chapterId: number): Promise<StoryboardProgress> => {
    try {
        const status = await request<StoryboardProgress>(`/novels/${novelId}/chapters/${chapterId}/storyboard-status`, {
            method: 'GET',
            headers: getHeaders(),
        });
        return status;
    } catch (error) {
        throw error;
    }
};
export interface Character {
    name: string;
    first_appearance: number;
    appearance_count: number;
    appearances: number[];
    description?: string;
    traits?: string[];
    aliases?: string[];
}

export interface Location {
    name: string;
    appearance_count: number;
    appearances: number[];
    description?: string;
}

export interface Item {
    name: string;
    first_appearance: number;
    description?: string;
}

export interface KeyEvent {
    summary: string;
    scene_index: number;
    importance?: string;
}

export interface TimelineEvent {
    time: string;
    event: string;
    scene_index: number;
}

export interface Scene {
    scene_index: number;
    original_text: string;
    summary: string;
    characters: string[];
    locations: string[];
    items: string[];
    key_events: string[];
    mood: string;
    time_period?: string;
}

export interface BibleData {
    characters: Character[];
    locations: Location[];
    items: Item[];
    key_events: KeyEvent[];
    timeline: TimelineEvent[];
    scenes?: Scene[]; // Added scenes field
    [key: string]: any; // Allow dynamic keys for custom analysis
}

export const getChapterBible = async (novelId: number, chapterId: number): Promise<BibleData> => {
    try {
        const bible = await request<BibleData>(`/novels/${novelId}/chapters/${chapterId}/bible`, {
            method: 'GET',
            headers: getHeaders(),
        });
        return bible;
    } catch (error) {
        throw error;
    }
};

export const reanalyzeChapter = async (novelId: number, chapterId: number): Promise<void> => {
    const response = await request<{ status: string }>(`/novels/${novelId}/chapters/${chapterId}/analyze`, {
        method: 'POST',
        headers: getHeaders(),
    });
};