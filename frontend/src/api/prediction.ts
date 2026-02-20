/**
 * Story Prediction API Service
 */

import { API_BASE_URL } from './client';

const PREDICTION_URL = `${PREDICTION_URL}/prediction`;

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
    const response = await fetch(`${PREDICTION_URL}/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ novel_id: novelId, text })
    });

    if (!response.ok) {
        throw new Error("Failed to start prediction task");
    }

    return response.json();
};

export const getPredictionTaskStatus = async (taskId: string): Promise<PredictionTaskResponse> => {
    const response = await fetch(`${PREDICTION_URL}/task/${taskId}`);

    if (!response.ok) {
        throw new Error("Failed to get task status");
    }

    return response.json();
};

export const getPredictionHistory = async (novelId: number): Promise<{ history: PredictionHistoryItem[] }> => {
    const response = await fetch(`${PREDICTION_URL}/history/${novelId}`);

    if (!response.ok) {
        throw new Error("Failed to get prediction history");
    }

    return response.json();
};

export const clearPredictionHistory = async (novelId: number): Promise<{ deleted: number }> => {
    const response = await fetch(`${PREDICTION_URL}/history/${novelId}`, {
        method: 'DELETE'
    });

    if (!response.ok) {
        throw new Error("Failed to clear prediction history");
    }

    return response.json();
};
