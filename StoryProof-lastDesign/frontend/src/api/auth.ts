import { request } from './client';
import { SignupRequest, UserResponse, LoginRequest, TokenResponse } from '../types/auth';

export async function register(data: SignupRequest): Promise<UserResponse> {
    return request<UserResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function login(data: LoginRequest): Promise<TokenResponse> {
    return request<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}
