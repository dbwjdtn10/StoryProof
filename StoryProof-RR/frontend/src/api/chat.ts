import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface ChatQuestionRequest {
    question: string;
    novel_filter?: string;
    alpha?: number;
    similarity_threshold?: number;
}

export interface ChatAnswerResponse {
    answer: string;
    source: {
        filename: string;
        scene_index?: number;
        total_scenes: number;
    } | null;
    similarity: number;
    found_context: boolean;
}

export const askQuestion = async (request: ChatQuestionRequest): Promise<ChatAnswerResponse> => {
    const response = await axios.post<ChatAnswerResponse>(
        `${API_BASE_URL}/chat/ask`,
        {
            question: request.question,
            novel_filter: request.novel_filter,
            alpha: request.alpha ?? 0.32,
            similarity_threshold: request.similarity_threshold ?? 0.5
        }
    );
    return response.data;
};
