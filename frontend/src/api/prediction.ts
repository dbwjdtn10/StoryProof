/**
 * Story Prediction API Service
 */

const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1/prediction`;

export interface PredictionTaskResponse {
    task_id: string;
    status: string;
    result?: string;
    error?: string;
}

export const requestPrediction = async (novelId: number, text: string): Promise<PredictionTaskResponse> => {
    const response = await fetch(`${API_BASE_URL}/request`, {
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
    const response = await fetch(`${API_BASE_URL}/task/${taskId}`);

    if (!response.ok) {
        throw new Error("Failed to get task status");
    }

    return response.json();
};
