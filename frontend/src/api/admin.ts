import { request } from './client';

// ===== 파트너 관리 API (관리자 전용) =====

export interface Partner {
    id: number;
    name: string;
    contact_email: string;
    plan: 'starter' | 'pro' | 'enterprise';
    monthly_quota: number;
    rate_limit_per_minute: number;
    is_active: boolean;
    created_at: string | null;
}

export interface PartnerCreateRequest {
    name: string;
    contact_email: string;
    plan: 'starter' | 'pro' | 'enterprise';
    monthly_quota: number;
    rate_limit_per_minute: number;
}

export interface PartnerCreateResponse {
    partner: Partner;
    api_key: string; // 이 응답에서만 확인 가능
}

export interface ApiKeyInfo {
    id: number;
    name: string;
    key_prefix: string;
    is_active: boolean;
    created_at: string | null;
    last_used_at: string | null;
}

export interface ApiKeyIssueResponse {
    key_info: ApiKeyInfo;
    api_key: string; // 이 응답에서만 확인 가능
}

export interface PartnerUsage {
    partner_id: number;
    partner_name: string;
    plan: string;
    monthly_quota: number;
    used_this_month: number;
    by_endpoint: { endpoint: string; calls: number; units: number }[];
}

export const listPartners = () =>
    request<Partner[]>('/admin/partners/');

export const createPartner = (data: PartnerCreateRequest) =>
    request<PartnerCreateResponse>('/admin/partners/', {
        method: 'POST',
        body: JSON.stringify(data),
    });

export const getPartnerUsage = (partnerId: number) =>
    request<PartnerUsage>(`/admin/partners/${partnerId}/usage`);

export const listApiKeys = (partnerId: number) =>
    request<ApiKeyInfo[]>(`/admin/partners/${partnerId}/keys`);

export const issueApiKey = (partnerId: number, name: string) =>
    request<ApiKeyIssueResponse>(
        `/admin/partners/${partnerId}/keys?name=${encodeURIComponent(name)}`,
        { method: 'POST' },
    );

export const revokeApiKey = (partnerId: number, keyId: number) =>
    request<void>(`/admin/partners/${partnerId}/keys/${keyId}`, {
        method: 'DELETE',
    });
