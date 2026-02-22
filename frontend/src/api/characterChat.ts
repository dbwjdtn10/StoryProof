import { request, getToken } from './client';
import { parseSSEBuffer } from './sseUtils';

export interface CharacterChatRoom {
    id: number;
    user_id: number;
    novel_id: number;
    chapter_id?: number;
    character_name: string;
    persona_prompt: string;
    created_at: string;
    updated_at?: string;
}

export interface CharacterChatMessage {
    id: number;
    room_id: number;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
}

export interface PersonaResponse {
    character_name: string;
    persona_prompt: string;
}

export const generatePersona = async (novelId: number, characterName: string, chapterId?: number): Promise<PersonaResponse> => {
    return request<PersonaResponse>('/character-chat/generate-persona', {
        method: 'POST',
        body: JSON.stringify({ novel_id: novelId, chapter_id: chapterId, character_name: characterName }),
    });
};

export const createRoom = async (novelId: number, characterName: string, personaPrompt: string, chapterId?: number): Promise<CharacterChatRoom> => {
    return request<CharacterChatRoom>('/character-chat/rooms', {
        method: 'POST',
        body: JSON.stringify({
            novel_id: novelId,
            chapter_id: chapterId,
            character_name: characterName,
            persona_prompt: personaPrompt
        }),
    });
};

export const getRooms = async (novelId: number, chapterId?: number): Promise<CharacterChatRoom[]> => {
    let url = `/character-chat/rooms?novel_id=${novelId}`;
    if (chapterId) {
        url += `&chapter_id=${chapterId}`;
    }
    return request<CharacterChatRoom[]>(url, {
        method: 'GET',
    });
};

export const sendMessage = async (roomId: number, content: string): Promise<CharacterChatMessage[]> => {
    return request<CharacterChatMessage[]>(`/character-chat/rooms/${roomId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content }),
    });
};

export const getMessages = async (roomId: number): Promise<CharacterChatMessage[]> => {
    return request<CharacterChatMessage[]>(`/character-chat/rooms/${roomId}/messages`, {
        method: 'GET',
    });
};

export const updateRoom = async (roomId: number, personaPrompt: string): Promise<CharacterChatRoom> => {
    return request<CharacterChatRoom>(`/character-chat/rooms/${roomId}`, {
        method: 'PUT',
        body: JSON.stringify({ persona_prompt: personaPrompt }),
    });
};

export const deleteRoom = async (roomId: number): Promise<void> => {
    return request<void>(`/character-chat/rooms/${roomId}`, {
        method: 'DELETE',
    });
};

const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1`;

/**
 * 캐릭터 챗 스트리밍 버전 (SSE)
 * 유저 메시지 저장 → AI 토큰 스트리밍 → AI 메시지 완료 순으로 콜백 호출
 */
export const sendMessageStream = async (
    roomId: number,
    content: string,
    onUserSaved: (msg: CharacterChatMessage) => void,
    onToken: (text: string) => void,
    onDone: (aiMsg: CharacterChatMessage) => void
): Promise<void> => {
    const token = getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE_URL}/character-chat/rooms/${roomId}/messages/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ content })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer = parseSSEBuffer(buffer, decoder.decode(value, { stream: true }), (parsed) => {
            if (parsed.type === 'user_saved') {
                onUserSaved({ id: parsed.id, room_id: roomId, role: 'user', content: parsed.content, created_at: parsed.created_at });
            } else if (parsed.type === 'token' && parsed.text) {
                onToken(parsed.text);
            } else if (parsed.type === 'done') {
                onDone({ id: parsed.ai_id, room_id: roomId, role: 'assistant', content: parsed.ai_content, created_at: parsed.created_at });
            }
        });
    }
};
