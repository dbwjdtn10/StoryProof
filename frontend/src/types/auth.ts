export interface User {
    id: number;
    email: string;
    username: string;
    user_mode: 'reader' | 'writer';
    is_active: boolean;
    created_at: string;
}

export interface SignupRequest {
    email: string;
    username: string;
    password: string;
    user_mode: 'reader' | 'writer';
}

export interface LoginRequest {
    email: string;
    password: string;
    remember_me?: boolean;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    refresh_token: string;
    user_mode: 'reader' | 'writer';
}

export interface UserResponse extends User { }
