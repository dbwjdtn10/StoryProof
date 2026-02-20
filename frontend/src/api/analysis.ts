/**
 * 설정파괴 분석 API 클라이언트
 */

import axios from 'axios';

export interface ConsistencyRequest {
    novel_id: number;
    chapter_id?: number;
    text: string;
}

export interface ConsistencyResult {
    status: 'SUCCESS' | 'FAILED' | 'PENDING' | 'PROCESSING';
    result?: {
        status: '설정 파괴 감지' | '설정 일치';
        results: Array<{
            type: '설정 충돌' | '개연성 경고';
            quote: string;
            description: string;
            suggestion: string;
        }>;
    };
    error?: string;
}

export interface PredictionRequest {
    novel_id: number;
    text: string;
}

export interface PredictionResult {
    status: 'COMPLETED';
    result: {
        prediction: string;
    };
}

/**
 * 설정 일관성 검사 요청
 */
export async function requestConsistencyCheck(data: ConsistencyRequest): Promise<{ task_id: string; status: string }> {
    const response = await axios.post(`/api/v1/analysis/consistency`, data);
    return response.data;
}

/**
 * 작업 결과 조회
 */
export async function getTaskResult(taskId: string): Promise<ConsistencyResult> {
    const response = await axios.get(`/api/v1/analysis/task/${taskId}`);
    return response.data;
}

/**
 * 스토리 예측 요청
 */
export async function requestPrediction(data: PredictionRequest): Promise<PredictionResult> {
    const response = await axios.post(`/api/v1/analysis/prediction`, data);
    return response.data;
}
