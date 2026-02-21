/**
 * Story Prediction API Service
 */

import { request } from './client';

export interface PredictionTaskResponse {
    task_id: string;
    status: string;
    result?: string;
    error?: string;
}

export interface PredictionHistoryItem {
    id: number;
    user_input: string;
    prediction: string;
    created_at: string | null;
}

export const requestPrediction = async (novelId: number, text: string): Promise<PredictionTaskResponse> => {
    return request<PredictionTaskResponse>('/prediction/request', {
        method: 'POST',
        body: JSON.stringify({ novel_id: novelId, text }),
    });
};

export const getPredictionTaskStatus = async (taskId: string): Promise<PredictionTaskResponse> => {
    return request<PredictionTaskResponse>(`/prediction/task/${taskId}`);
};

export const getPredictionHistory = async (novelId: number): Promise<{ history: PredictionHistoryItem[] }> => {
    return request<{ history: PredictionHistoryItem[] }>(`/prediction/history/${novelId}`);
};

export const clearPredictionHistory = async (novelId: number): Promise<{ deleted: number }> => {
    return request<{ deleted: number }>(`/prediction/history/${novelId}`, {
        method: 'DELETE',
    });
};
