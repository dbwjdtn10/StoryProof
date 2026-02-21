/**
 * 설정파괴 분석 API 클라이언트
 */

import { request } from './client';

export interface ConsistencyRequest {
    novel_id: number;
    chapter_id?: number;
    text: string;
}

export interface ConsistencyResult {
    status: 'COMPLETED' | 'FAILED' | 'PENDING' | 'PROCESSING';
    result?: {
        status: '설정 파괴 감지' | '설정 일치';
        results: Array<{
            type: '설정 충돌' | '개연성 경고';
            severity?: '치명적' | '주의' | '참고';
            quote: string;
            evidence?: string;
            description: string;
            suggestion: string;
        }>;
    };
    error?: string;
}

export interface ChapterAnalysisRequest {
    novel_id: number;
    chapter_id: number;
    analysis_type: 'plot' | 'style' | 'overall' | 'consistency';
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
 * 설정 파괴 분석 캐시 조회
 */
export async function getCachedConsistency(novelId: number, chapterId: number): Promise<{ cached: boolean; result: any }> {
    return request<{ cached: boolean; result: any }>(`/analysis/consistency/${novelId}/${chapterId}`);
}

/**
 * 설정 일관성 검사 요청
 */
export async function requestConsistencyCheck(data: ConsistencyRequest): Promise<{ task_id: string; status: string }> {
    return request<{ task_id: string; status: string }>('/analysis/consistency', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

/**
 * 작업 결과 조회
 */
export async function getTaskResult(taskId: string): Promise<ConsistencyResult> {
    return request<ConsistencyResult>(`/analysis/task/${taskId}`);
}

/**
 * 스토리 예측 요청
 */
export async function requestPrediction(data: PredictionRequest): Promise<PredictionResult> {
    return request<PredictionResult>('/analysis/prediction', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

/**
 * 회차 분석 요청 (플롯/문체/종합)
 */
export async function requestChapterAnalysis(data: ChapterAnalysisRequest): Promise<{ task_id: string; status: string; analysis_id: number }> {
    return request<{ task_id: string; status: string; analysis_id: number }>('/analysis/chapter-analysis', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

/**
 * 회차 분석 캐시 조회
 */
export async function getCachedChapterAnalysis(novelId: number, chapterId: number, analysisType: string): Promise<{ cached: boolean; result: any }> {
    return request<{ cached: boolean; result: any }>(`/analysis/chapter-analysis/${novelId}/${chapterId}/${analysisType}`);
}
