import { request, getToken } from './client';


// Define types for image generation
export interface ImageGenerationRequest {
    novel_id: number;
    chapter_id?: number;
    entity_type: 'character' | 'item' | 'location'; // text matches backend enum names or strings
    entity_name: string;
    description: string;
}

export interface ImageGenerationResponse {
    image_url: string;
    message: string;
}

// Helper to get headers with auth token
const getHeaders = (): Record<string, string> => {
    const token = getToken();
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    };
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

/**
 * Generate an image for a specific entity (Character, Item, Location)
 */
export const generateImage = async (data: ImageGenerationRequest): Promise<ImageGenerationResponse> => {
    return request<ImageGenerationResponse>('/images/generate', {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
};
