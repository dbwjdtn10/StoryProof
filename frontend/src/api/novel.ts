
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

export const getNovels = async (skip = 0, limit = 10): Promise<NovelListResponse> => {
    return request<NovelListResponse>(`/novels/?skip=${skip}&limit=${limit}`, { method: 'GET' });
};

export const createNovel = async (data: { title: string; description?: string; genre?: string; is_public?: boolean }) => {
    return request<Novel>('/novels/', { method: 'POST', body: JSON.stringify(data) });
};

export const getChapters = async (novelId: number): Promise<Chapter[]> => {
    return request<Chapter[]>(`/novels/${novelId}/chapters`, { method: 'GET' });
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

    const response = await fetch(`/api/v1/novels/${novelId}/chapters/upload`, {
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

    return request<Chapter>(`/novels/${novelId}/chapters/${chapterId}`, { method: 'GET' });
};

export const updateChapter = async (novelId: number, chapterId: number, data: { title?: string; content?: string }) => {
    return request<Chapter>(`/novels/${novelId}/chapters/${chapterId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
};

export const deleteChapter = async (novelId: number, chapterId: number): Promise<void> => {
    return request<void>(`/novels/${novelId}/chapters/${chapterId}`, { method: 'DELETE' });
};

export const getStoryboardStatus = async (novelId: number, chapterId: number): Promise<StoryboardProgress> => {
    return request<StoryboardProgress>(`/novels/${novelId}/chapters/${chapterId}/storyboard-status`, { method: 'GET' });
};
export interface Character {
    name: string;
    first_appearance: number;
    appearance_count: number;
    appearances: number[];
    description?: string;
    traits?: string[];
    aliases?: string[];
    image?: string; // Generated image URL
}

export interface Location {
    name: string;
    appearance_count: number;
    appearances: number[];
    description?: string;
    image?: string; // Generated image URL
}

export interface Item {
    name: string;
    first_appearance: number;
    description?: string;
    image?: string; // Generated image URL
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
    return request<BibleData>(`/novels/${novelId}/chapters/${chapterId}/bible`, { method: 'GET' });
};

export const reanalyzeChapter = async (novelId: number, chapterId: number): Promise<void> => {
    await request<{ status: string }>(`/novels/${novelId}/chapters/${chapterId}/analyze`, { method: 'POST' });
};

export const mergeChapters = async (novelId: number, targetId: number, sourceIds: number[]): Promise<Chapter> => {
    return request<Chapter>(`/novels/${novelId}/merge-contents`, {
        method: 'PATCH',
        body: JSON.stringify({ target_id: targetId, source_ids: sourceIds }),
    });
};