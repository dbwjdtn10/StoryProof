const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1`;


export async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    console.log("API Request:", { url, method: options?.method || 'GET' });

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error("API Error Response:", { url, status: response.status, errorData });
        throw new Error(errorData.detail || `API request failed: ${response.statusText}`);
    }

    // 204 No Content는 body가 없으므로 특별히 처리
    if (response.status === 204) {
        console.log("API Response: 204 No Content (success)");
        return undefined as unknown as T;
    }

    const data = await response.json();
    console.log("API Response:", { url, data });
    return data;
}
