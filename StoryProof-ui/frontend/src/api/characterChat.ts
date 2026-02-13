//HJE
import { request } from './client';

export interface CharacterChatRoom {
    id: number;
    user_id: number;
    novel_id: number;
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

const getHeaders = (): Record<string, string> => {
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

export const generatePersona = async (novelId: number, characterName: string): Promise<PersonaResponse> => {
    return request<PersonaResponse>('/character-chat/generate-persona', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ novel_id: novelId, character_name: characterName }),
    });
};

export const createRoom = async (novelId: number, characterName: string, personaPrompt: string): Promise<CharacterChatRoom> => {
    return request<CharacterChatRoom>('/character-chat/rooms', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
            novel_id: novelId,
            character_name: characterName,
            persona_prompt: personaPrompt
        }),
    });
};

export const getRooms = async (novelId: number): Promise<CharacterChatRoom[]> => {
    return request<CharacterChatRoom[]>(`/character-chat/rooms?novel_id=${novelId}`, {
        method: 'GET',
        headers: getHeaders(),
    });
};

export const sendMessage = async (roomId: number, content: string): Promise<CharacterChatMessage[]> => {
    return request<CharacterChatMessage[]>(`/character-chat/rooms/${roomId}/messages`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ content }),
    });
};

export const getMessages = async (roomId: number): Promise<CharacterChatMessage[]> => {
    return request<CharacterChatMessage[]>(`/character-chat/rooms/${roomId}/messages`, {
        method: 'GET',
        headers: getHeaders(),
    });
};

export const updateRoom = async (roomId: number, personaPrompt: string): Promise<CharacterChatRoom> => {
    return request<CharacterChatRoom>(`/character-chat/rooms/${roomId}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({ persona_prompt: personaPrompt }),
    });
};

export const deleteRoom = async (roomId: number): Promise<void> => {
    return request<void>(`/character-chat/rooms/${roomId}`, {
        method: 'DELETE',
        headers: getHeaders(),
    });
};
