const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1`;


export async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    const token = localStorage.getItem('token');
    const authHeader: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...authHeader,
            ...options?.headers, // 호출부에서 명시적으로 전달한 헤더가 우선
        },
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error("API Error:", { url, status: response.status, detail: errorData.detail });
        throw new Error(errorData.detail || `API request failed: ${response.statusText}`);
    }

    if (response.status === 204) {
        return undefined as unknown as T;
    }

    return response.json();
}
