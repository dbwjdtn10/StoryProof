import axios from 'axios';

const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1`;

export interface ChatQuestionRequest {
    question: string;
    novel_id?: number;
    chapter_id?: number;
    novel_filter?: string;
    alpha?: number;
    similarity_threshold?: number;
}

export interface ChatAnswerResponse {
    answer: string;
    source: {
        filename: string;
        scene_index?: number;
        chapter_id?: number;
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
            novel_id: request.novel_id,
            chapter_id: request.chapter_id,
            novel_filter: request.novel_filter,
            alpha: request.alpha ?? 0.32,
            similarity_threshold: request.similarity_threshold ?? 0.5
        }
    );
    return response.data;
};

export interface StreamMeta {
    source: ChatAnswerResponse['source'];
    similarity: number;
    found_context: boolean;
}

/**
 * Q&A 챗봇 스트리밍 버전 (SSE)
 * LLM 응답을 토큰 단위로 받아 onToken 콜백으로 전달합니다.
 */
export const askQuestionStream = async (
    request: ChatQuestionRequest,
    onToken: (text: string) => void,
    onMeta: (meta: StreamMeta) => void,
    onDone: () => void
): Promise<void> => {
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE_URL}/chat/ask/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
            question: request.question,
            novel_id: request.novel_id,
            chapter_id: request.chapter_id,
            novel_filter: request.novel_filter,
            alpha: request.alpha ?? 0.32,
            similarity_threshold: request.similarity_threshold ?? 0.5
        })
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

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6).trim();
            if (data === '[DONE]') { onDone(); return; }
            try {
                const parsed = JSON.parse(data);
                if (parsed.type === 'meta') onMeta(parsed as StreamMeta);
                else if (parsed.type === 'token' && parsed.text) onToken(parsed.text);
            } catch { /* ignore parse errors */ }
        }
    }
    onDone();
};
