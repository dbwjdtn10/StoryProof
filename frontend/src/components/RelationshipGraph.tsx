import { useState, useRef, useEffect, useCallback } from 'react';
import { X, Network } from 'lucide-react';

interface Relationship {
    source?: string;
    target?: string;
    character1?: string;
    character2?: string;
    relation?: string;
    description?: string;
}

interface CharacterInfo {
    name: string;
    description?: string;
    traits?: string[];
}

interface RelationshipGraphModalProps {
    isOpen: boolean;
    onClose: () => void;
    relationships: Relationship[];
    characters?: CharacterInfo[];
}

const NODE_COLORS = [
    '#4F46E5', '#DC2626', '#059669', '#D97706', '#7C3AED',
    '#DB2777', '#0891B2', '#65A30D', '#EA580C', '#6366F1',
    '#14B8A6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899',
];

interface NodeData {
    name: string;
    x: number;
    y: number;
    color: string;
    description: string;
    initials: string;
}

export function RelationshipGraphModal({ isOpen, onClose, relationships, characters = [] }: RelationshipGraphModalProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const [selectedNode, setSelectedNode] = useState<string | null>(null);
    const [canvasSize, setCanvasSize] = useState({ w: 800, h: 600 });
    const nodesRef = useRef<NodeData[]>([]);
    const animFrameRef = useRef<number>(0);

    // 캐릭터 정보 맵 생성
    const charMap = useRef<Map<string, CharacterInfo>>(new Map());

    useEffect(() => {
        const map = new Map<string, CharacterInfo>();
        for (const c of characters) map.set(c.name, c);
        charMap.current = map;
    }, [characters]);

    // 캔버스 크기 동적 계산
    useEffect(() => {
        if (!isOpen || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        setCanvasSize({ w: rect.width, h: rect.height });
    }, [isOpen]);

    // 노드 배치 계산
    useEffect(() => {
        if (!isOpen) return;
        const nameSet = new Set<string>();
        for (const r of relationships) {
            const src = r.source || r.character1 || '';
            const tgt = r.target || r.character2 || '';
            if (src) nameSet.add(src);
            if (tgt) nameSet.add(tgt);
        }
        const names = Array.from(nameSet);
        const { w, h } = canvasSize;
        const cx = w / 2;
        const cy = h / 2;
        const radius = Math.min(w, h) * 0.35;
        const count = names.length;

        nodesRef.current = names.map((name, i) => {
            const info = charMap.current.get(name);
            const angle = (2 * Math.PI * i) / count - Math.PI / 2;
            return {
                name,
                x: cx + radius * Math.cos(angle),
                y: cy + radius * Math.sin(angle),
                color: NODE_COLORS[i % NODE_COLORS.length],
                description: info?.description || '',
                initials: name.slice(0, 2),
            };
        });
    }, [isOpen, relationships, canvasSize]);

    const getNode = useCallback((name: string) => {
        return nodesRef.current.find(n => n.name === name);
    }, []);

    // Canvas 렌더링
    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const { w, h } = canvasSize;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, w, h);

        const nodeR = Math.max(28, Math.min(40, w / (nodesRef.current.length * 2.5)));

        // 엣지
        for (const rel of relationships) {
            const src = getNode(rel.source || rel.character1 || '');
            const tgt = getNode(rel.target || rel.character2 || '');
            if (!src || !tgt) continue;

            const isHL = hoveredNode === src.name || hoveredNode === tgt.name ||
                selectedNode === src.name || selectedNode === tgt.name;
            const dimmed = (hoveredNode || selectedNode) && !isHL;

            // 곡선 엣지 (같은 위치 방지)
            const mx = (src.x + tgt.x) / 2;
            const my = (src.y + tgt.y) / 2;

            ctx.beginPath();
            ctx.moveTo(src.x, src.y);
            ctx.lineTo(tgt.x, tgt.y);
            ctx.strokeStyle = dimmed ? 'rgba(180,180,180,0.15)' : isHL ? src.color : 'rgba(150,150,150,0.5)';
            ctx.lineWidth = isHL ? 3 : 1.5;
            if (!dimmed) {
                ctx.setLineDash([]);
            } else {
                ctx.setLineDash([4, 4]);
            }
            ctx.stroke();
            ctx.setLineDash([]);

            // 관계 라벨
            if (rel.relation && !dimmed) {
                const lx = mx;
                const ly = my;
                ctx.font = `${isHL ? 'bold ' : ''}${isHL ? 13 : 11}px Pretendard, "Noto Sans KR", sans-serif`;
                const text = rel.relation;
                const tm = ctx.measureText(text);
                const pad = 5;

                // 라벨 배경 (둥근 사각형)
                const rx = lx - tm.width / 2 - pad;
                const ry = ly - 8 - pad;
                const rw = tm.width + pad * 2;
                const rh = 16 + pad * 2;
                ctx.fillStyle = isHL ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.85)';
                ctx.beginPath();
                ctx.roundRect(rx, ry, rw, rh, 4);
                ctx.fill();
                if (isHL) {
                    ctx.strokeStyle = src.color;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }

                ctx.fillStyle = isHL ? src.color : '#666';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, lx, ly);
            }
        }

        // 노드
        for (const node of nodesRef.current) {
            const isHL = hoveredNode === node.name || selectedNode === node.name;
            const dimmed = (hoveredNode || selectedNode) && !isHL &&
                !relationships.some(r => {
                    const s = r.source || r.character1 || '';
                    const t = r.target || r.character2 || '';
                    return (s === node.name && (t === hoveredNode || t === selectedNode)) ||
                        (t === node.name && (s === hoveredNode || s === selectedNode));
                });

            const r = isHL ? nodeR + 6 : nodeR;

            // 그림자
            ctx.shadowColor = isHL ? `${node.color}66` : 'rgba(0,0,0,0.08)';
            ctx.shadowBlur = isHL ? 20 : 6;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = isHL ? 0 : 3;

            // 외곽 링
            if (isHL) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 4, 0, Math.PI * 2);
                ctx.fillStyle = `${node.color}22`;
                ctx.fill();
            }

            // 원
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
            ctx.fillStyle = dimmed ? '#ccc' : node.color;
            ctx.fill();
            ctx.shadowColor = 'transparent';

            // 테두리
            ctx.strokeStyle = dimmed ? '#bbb' : '#fff';
            ctx.lineWidth = 3;
            ctx.stroke();

            // 이니셜
            ctx.font = `bold ${Math.round(r * 0.6)}px Pretendard, "Noto Sans KR", sans-serif`;
            ctx.fillStyle = '#fff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(node.initials, node.x, node.y);

            // 이름 라벨
            ctx.font = `${isHL ? 'bold ' : ''}${isHL ? 14 : 12}px Pretendard, "Noto Sans KR", sans-serif`;
            ctx.fillStyle = dimmed ? '#aaa' : 'var(--foreground, #333)';
            ctx.textBaseline = 'top';
            ctx.fillText(node.name, node.x, node.y + r + 8);
        }
    }, [relationships, hoveredNode, selectedNode, canvasSize, getNode]);

    useEffect(() => {
        if (!isOpen) return;
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = requestAnimationFrame(draw);
    }, [draw, isOpen]);

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        let found: string | null = null;
        const nodeR = Math.max(28, Math.min(40, canvasSize.w / (nodesRef.current.length * 2.5)));
        for (const node of nodesRef.current) {
            const dx = mx - node.x;
            const dy = my - node.y;
            if (dx * dx + dy * dy < (nodeR + 10) * (nodeR + 10)) {
                found = node.name;
                break;
            }
        }
        setHoveredNode(found);
    }, [canvasSize]);

    const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        const nodeR = Math.max(28, Math.min(40, canvasSize.w / (nodesRef.current.length * 2.5)));
        for (const node of nodesRef.current) {
            const dx = mx - node.x;
            const dy = my - node.y;
            if (dx * dx + dy * dy < (nodeR + 10) * (nodeR + 10)) {
                setSelectedNode(prev => prev === node.name ? null : node.name);
                return;
            }
        }
        setSelectedNode(null);
    }, [canvasSize]);

    if (!isOpen) return null;

    const activeNode = selectedNode || hoveredNode;
    const activeInfo = activeNode ? charMap.current.get(activeNode) : null;
    const activeRels = activeNode ? relationships.filter(r => {
        const s = r.source || r.character1 || '';
        const t = r.target || r.character2 || '';
        return s === activeNode || t === activeNode;
    }) : [];

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 1100,
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: 'fadeIn 0.2s ease'
        }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div style={{
                width: '90vw', maxWidth: '1100px', height: '80vh', maxHeight: '750px',
                background: 'var(--modal-bg, #fff)', borderRadius: '16px',
                border: '1px solid var(--modal-border, #e5e7eb)',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                display: 'flex', flexDirection: 'column', overflow: 'hidden'
            }}>
                {/* 헤더 */}
                <div style={{
                    padding: '16px 24px', borderBottom: '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'var(--modal-header-bg)', color: 'var(--modal-header-text)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Network size={22} />
                        <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700 }}>인물 관계도</h2>
                        <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>
                            {nodesRef.current.length}명 · {relationships.length}개 관계
                        </span>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'currentColor', padding: '4px'
                    }}>
                        <X size={22} />
                    </button>
                </div>

                {/* 본체 */}
                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    {/* Canvas 영역 */}
                    <div ref={containerRef} style={{ flex: 1, position: 'relative', minHeight: 0 }}>
                        {relationships.length === 0 ? (
                            <div style={{
                                height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                color: 'var(--muted-foreground)', fontSize: '0.95rem'
                            }}>
                                관계 데이터가 없습니다. 바이블을 먼저 생성해주세요.
                            </div>
                        ) : (
                            <canvas
                                ref={canvasRef}
                                style={{
                                    width: '100%', height: '100%',
                                    cursor: hoveredNode ? 'pointer' : 'default'
                                }}
                                onMouseMove={handleMouseMove}
                                onClick={handleClick}
                                onMouseLeave={() => setHoveredNode(null)}
                            />
                        )}
                    </div>

                    {/* 사이드 정보 패널 */}
                    {activeNode && (
                        <div style={{
                            width: '260px', borderLeft: '1px solid var(--border)',
                            padding: '20px', overflowY: 'auto',
                            background: 'var(--card-bg, #fafafa)'
                        }}>
                            <div style={{
                                width: '64px', height: '64px', borderRadius: '50%',
                                background: getNode(activeNode)?.color || '#4F46E5',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                margin: '0 auto 12px', color: '#fff',
                                fontSize: '1.5rem', fontWeight: 700
                            }}>
                                {activeNode.slice(0, 2)}
                            </div>
                            <h3 style={{ textAlign: 'center', margin: '0 0 8px', fontSize: '1.1rem' }}>
                                {activeNode}
                            </h3>
                            {activeInfo?.description && (
                                <p style={{ fontSize: '0.82rem', color: 'var(--muted-foreground)', lineHeight: 1.5, margin: '0 0 12px' }}>
                                    {activeInfo.description}
                                </p>
                            )}
                            {activeInfo?.traits && activeInfo.traits.length > 0 && (
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '16px' }}>
                                    {activeInfo.traits.map((t, i) => (
                                        <span key={i} style={{
                                            fontSize: '0.72rem', padding: '2px 8px',
                                            borderRadius: '10px', background: 'var(--primary, #4F46E5)',
                                            color: '#fff', fontWeight: 600
                                        }}>{t}</span>
                                    ))}
                                </div>
                            )}
                            {activeRels.length > 0 && (
                                <>
                                    <h4 style={{ fontSize: '0.85rem', margin: '0 0 8px', fontWeight: 700 }}>관계</h4>
                                    {activeRels.map((r, i) => {
                                        const other = (r.source || r.character1) === activeNode
                                            ? (r.target || r.character2)
                                            : (r.source || r.character1);
                                        return (
                                            <div key={i} style={{
                                                padding: '8px', marginBottom: '6px',
                                                borderRadius: '8px', fontSize: '0.8rem',
                                                border: '1px solid var(--border)',
                                                background: 'var(--modal-bg, #fff)'
                                            }}>
                                                <div style={{ fontWeight: 600 }}>
                                                    → {other}
                                                    <span style={{
                                                        marginLeft: '6px', fontSize: '0.72rem',
                                                        padding: '1px 6px', borderRadius: '8px',
                                                        background: 'var(--primary, #4F46E5)', color: '#fff'
                                                    }}>{r.relation || '관계'}</span>
                                                </div>
                                                {r.description && (
                                                    <div style={{ marginTop: '4px', color: 'var(--muted-foreground)', lineHeight: 1.4 }}>
                                                        {r.description}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
