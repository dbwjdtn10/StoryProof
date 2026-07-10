/**
 * 관리자 대시보드 — B2B 파트너 관리
 * - 파트너 목록/등록, API 키 발급·폐기, 월간 사용량(쿼터 대비) 시각화
 * - 접근: is_admin 사용자 전용 (백엔드에서도 require_admin으로 이중 차단)
 */
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { ArrowLeft, Building2, Copy, KeyRound, Plus, RefreshCw, Trash2 } from 'lucide-react';
import {
    Partner, PartnerUsage, ApiKeyInfo,
    listPartners, createPartner, getPartnerUsage,
    listApiKeys, issueApiKey, revokeApiKey,
} from '../api/admin';
import './AdminDashboard.css';

interface AdminDashboardProps {
    onBack: () => void;
}

const EMPTY_FORM = {
    name: '',
    contact_email: '',
    plan: 'starter' as Partner['plan'],
    monthly_quota: 10000,
    rate_limit_per_minute: 60,
};

function copyToClipboard(text: string, label: string) {
    navigator.clipboard.writeText(text)
        .then(() => toast.success(`${label}가 복사되었습니다.`))
        .catch(() => toast.error('복사에 실패했습니다. 직접 선택해 복사해주세요.'));
}

export function AdminDashboard({ onBack }: AdminDashboardProps) {
    const [partners, setPartners] = useState<Partner[]>([]);
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [usage, setUsage] = useState<PartnerUsage | null>(null);
    const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
    const [loading, setLoading] = useState(false);

    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState(EMPTY_FORM);
    const [submitting, setSubmitting] = useState(false);
    // 발급 직후 1회만 노출되는 원본 API 키
    const [issuedKey, setIssuedKey] = useState<string | null>(null);

    const loadPartners = useCallback(async () => {
        try {
            const list = await listPartners();
            setPartners(list);
            if (list.length > 0 && selectedId === null) {
                setSelectedId(list[0].id);
            }
        } catch (e) {
            toast.error(e instanceof Error ? e.message : '파트너 목록 조회 실패');
        }
    }, [selectedId]);

    const loadDetail = useCallback(async (partnerId: number) => {
        setLoading(true);
        try {
            const [u, k] = await Promise.all([
                getPartnerUsage(partnerId),
                listApiKeys(partnerId),
            ]);
            setUsage(u);
            setKeys(k);
        } catch (e) {
            toast.error(e instanceof Error ? e.message : '파트너 상세 조회 실패');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadPartners(); }, [loadPartners]);
    useEffect(() => {
        if (selectedId !== null) {
            setIssuedKey(null);
            loadDetail(selectedId);
        }
    }, [selectedId, loadDetail]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (submitting) return;
        setSubmitting(true);
        try {
            const res = await createPartner(form);
            toast.success(`파트너 "${res.partner.name}" 등록 완료`);
            setShowForm(false);
            setForm(EMPTY_FORM);
            await loadPartners();
            setSelectedId(res.partner.id);
            setIssuedKey(res.api_key);
        } catch (e) {
            toast.error(e instanceof Error ? e.message : '파트너 등록 실패');
        } finally {
            setSubmitting(false);
        }
    };

    const handleIssueKey = async () => {
        if (selectedId === null) return;
        const name = window.prompt('새 키 이름 (예: rotation-2026-07)', 'rotation');
        if (!name) return;
        try {
            const res = await issueApiKey(selectedId, name);
            setIssuedKey(res.api_key);
            await loadDetail(selectedId);
            toast.success('새 API 키가 발급되었습니다. 지금 복사해 전달하세요.');
        } catch (e) {
            toast.error(e instanceof Error ? e.message : '키 발급 실패');
        }
    };

    const handleRevokeKey = async (key: ApiKeyInfo) => {
        if (selectedId === null) return;
        if (!window.confirm(`키 "${key.name}" (${key.key_prefix}…)를 폐기할까요?\n폐기 즉시 해당 키의 모든 요청이 거부됩니다.`)) return;
        try {
            await revokeApiKey(selectedId, key.id);
            await loadDetail(selectedId);
            toast.success('키가 폐기되었습니다.');
        } catch (e) {
            toast.error(e instanceof Error ? e.message : '키 폐기 실패');
        }
    };

    const usedRatio = usage && usage.monthly_quota > 0
        ? Math.min(100, Math.round(usage.used_this_month / usage.monthly_quota * 100))
        : 0;
    const barClass = usedRatio >= 100 ? 'over' : usedRatio >= 80 ? 'warn' : '';

    return (
        <div className="admin-container">
            <div className="admin-header">
                <h1>
                    <button className="admin-btn" onClick={onBack} title="돌아가기">
                        <ArrowLeft size={16} />
                    </button>
                    <Building2 size={20} />
                    파트너 관리
                </h1>
                <button className="admin-btn primary" onClick={() => setShowForm(v => !v)}>
                    <Plus size={16} /> 새 파트너 등록
                </button>
            </div>

            <div className="admin-body">
                {/* 좌측: 파트너 목록 + 등록 폼 */}
                <div>
                    {showForm && (
                        <div className="admin-card" style={{ marginBottom: 16 }}>
                            <h2>새 파트너 등록</h2>
                            <form className="admin-form" onSubmit={handleCreate}>
                                <label>파트너 이름</label>
                                <input required value={form.name} placeholder="카카오페이지"
                                    onChange={e => setForm({ ...form, name: e.target.value })} />
                                <label>담당자 이메일</label>
                                <input required type="email" value={form.contact_email} placeholder="biz@partner.com"
                                    onChange={e => setForm({ ...form, contact_email: e.target.value })} />
                                <label>플랜</label>
                                <select value={form.plan}
                                    onChange={e => setForm({ ...form, plan: e.target.value as Partner['plan'] })}>
                                    <option value="starter">Starter</option>
                                    <option value="pro">Pro</option>
                                    <option value="enterprise">Enterprise</option>
                                </select>
                                <label>월간 쿼터 (units)</label>
                                <input required type="number" min={1} value={form.monthly_quota}
                                    onChange={e => setForm({ ...form, monthly_quota: Number(e.target.value) })} />
                                <label>분당 요청 한도</label>
                                <input required type="number" min={1} value={form.rate_limit_per_minute}
                                    onChange={e => setForm({ ...form, rate_limit_per_minute: Number(e.target.value) })} />
                                <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
                                    <button type="submit" className="admin-btn primary" disabled={submitting}>
                                        {submitting ? '등록 중...' : '등록'}
                                    </button>
                                    <button type="button" className="admin-btn" onClick={() => setShowForm(false)}>
                                        취소
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}

                    <div className="admin-card">
                        <h2>파트너 ({partners.length})</h2>
                        {partners.length === 0 && (
                            <div className="admin-empty">등록된 파트너가 없습니다.</div>
                        )}
                        {partners.map(p => (
                            <button key={p.id}
                                className={`partner-item ${selectedId === p.id ? 'selected' : ''}`}
                                onClick={() => setSelectedId(p.id)}>
                                <div className="partner-name">
                                    <span>{p.name}{!p.is_active && ' (비활성)'}</span>
                                    <span className={`plan-badge ${p.plan}`}>{p.plan}</span>
                                </div>
                                <div className="partner-meta">{p.contact_email}</div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* 우측: 선택 파트너 상세 */}
                <div>
                    {issuedKey && (
                        <div className="secret-box" style={{ marginBottom: 16 }}>
                            ⚠️ <b>새 API 키 — 지금만 확인할 수 있습니다.</b> 안전한 채널로 파트너에게 전달하세요.
                            <code>{issuedKey}</code>
                            <button className="admin-btn" onClick={() => copyToClipboard(issuedKey, 'API 키')}>
                                <Copy size={14} /> 복사
                            </button>
                        </div>
                    )}

                    {selectedId === null ? (
                        <div className="admin-card admin-empty">좌측에서 파트너를 선택하세요.</div>
                    ) : (
                        <>
                            <div className="admin-card" style={{ marginBottom: 16 }}>
                                <h2 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    이번 달 사용량
                                    <button className="admin-btn" onClick={() => loadDetail(selectedId)} disabled={loading}>
                                        <RefreshCw size={14} /> 새로고침
                                    </button>
                                </h2>
                                {usage && (
                                    <>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                                            <span><b>{usage.used_this_month.toLocaleString()}</b> / {usage.monthly_quota.toLocaleString()} units</span>
                                            <span>{usedRatio}%</span>
                                        </div>
                                        <div className="usage-bar-track">
                                            <div className={`usage-bar-fill ${barClass}`} style={{ width: `${usedRatio}%` }} />
                                        </div>
                                        {usage.by_endpoint.length > 0 ? (
                                            <table className="admin-table" style={{ marginTop: 12 }}>
                                                <thead>
                                                    <tr><th>엔드포인트</th><th>호출 수</th><th>과금 units</th></tr>
                                                </thead>
                                                <tbody>
                                                    {usage.by_endpoint.map(row => (
                                                        <tr key={row.endpoint}>
                                                            <td>{row.endpoint}</td>
                                                            <td>{row.calls.toLocaleString()}</td>
                                                            <td>{row.units.toLocaleString()}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        ) : (
                                            <div className="admin-empty">이번 달 사용 내역이 없습니다.</div>
                                        )}
                                    </>
                                )}
                            </div>

                            <div className="admin-card">
                                <h2 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    API 키
                                    <button className="admin-btn" onClick={handleIssueKey}>
                                        <KeyRound size={14} /> 새 키 발급
                                    </button>
                                </h2>
                                {keys.length === 0 ? (
                                    <div className="admin-empty">발급된 키가 없습니다.</div>
                                ) : (
                                    <table className="admin-table">
                                        <thead>
                                            <tr><th>이름</th><th>키</th><th>마지막 사용</th><th></th></tr>
                                        </thead>
                                        <tbody>
                                            {keys.map(k => (
                                                <tr key={k.id} className={k.is_active ? '' : 'key-revoked'}>
                                                    <td>{k.name}</td>
                                                    <td><code>{k.key_prefix}…</code></td>
                                                    <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : '-'}</td>
                                                    <td style={{ textAlign: 'right' }}>
                                                        {k.is_active && (
                                                            <button className="admin-btn danger" onClick={() => handleRevokeKey(k)} title="키 폐기">
                                                                <Trash2 size={14} />
                                                            </button>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
