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

export const requestPrediction = async (novelId: number, text: string): Promise<PredictionTaskResponse> => {
    return request<PredictionTaskResponse>('/prediction/request', {
        method: 'POST',
        body: JSON.stringify({ novel_id: novelId, text })
    });
};

export const getPredictionTaskStatus = async (taskId: string): Promise<PredictionTaskResponse> => {
    return request<PredictionTaskResponse>(`/prediction/task/${taskId}`);
};
