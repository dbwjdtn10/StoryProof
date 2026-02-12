import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface ImageTaskResponse {
    task_id: string;
    status: string;
}

export interface ImageResultResponse {
    status: string;
    image_url?: string;
    message?: string;
}

// 1. 이미지 생성 작업 요청
export const requestImageGeneration = async (prompt: string): Promise<ImageTaskResponse> => {
    const response = await axios.post(`${API_BASE_URL}/image/generate-image`, { prompt }); 
    return response.data;
};

// 2. 이미지 생성 상태 확인
export const getImageTaskStatus = async (taskId: string): Promise<ImageResultResponse> => {
    const response = await axios.get(`${API_BASE_URL}/image/generate-image/${taskId}`);
    return response.data;
};

export const refinePromptWithGemini = async (prompt: string): Promise<string> => {
    const response = await axios.post(`${API_BASE_URL}/image/refine`, { prompt });
    return response.data.refinedPrompt;
};