export const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1`;

export function getToken(): string | null {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
}

export function clearAuth() {
    localStorage.removeItem('token');
    localStorage.removeItem('userMode');
    localStorage.removeItem('remembered');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('userMode');
}

export async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const token = getToken();

    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options?.headers,
        },
    });

    if (!response.ok) {
        if (response.status === 401) {
            clearAuth();
            window.location.href = '/';
            throw new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API request failed: ${response.statusText}`);
    }

    if (response.status === 204) {
        return undefined as unknown as T;
    }

    const data = await response.json();
    return data;
}
