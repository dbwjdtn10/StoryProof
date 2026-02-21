import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { X, Network, Check } from 'lucide-react';

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
    initials: string;
}

function getSrc(r: Relationship) { return r.source || r.character1 || ''; }
function getTgt(r: Relationship) { return r.target || r.character2 || ''; }

export function RelationshipGraphModal({ isOpen, onClose, relationships, characters = [] }: RelationshipGraphModalProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const [canvasSize, setCanvasSize] = useState({ w: 600, h: 500 });
    const nodesRef = useRef<NodeData[]>([]);
    const animFrameRef = useRef<number>(0);

    // 전체 인물 목록 (관계에 등장하는 인물)
    const allNames = useMemo(() => {
        const set = new Set<string>();
        for (const r of relationships) {
            const s = getSrc(r), t = getTgt(r);
            if (s) set.add(s);
            if (t) set.add(t);
        }
        return Array.from(set);
    }, [relationships]);

    // 색상 맵 (일관된 색상 유지)
    const colorMap = useMemo(() => {
        const map = new Map<string, string>();
        allNames.forEach((name, i) => map.set(name, NODE_COLORS[i % NODE_COLORS.length]));
        return map;
    }, [allNames]);

    // 캐릭터 정보 맵
    const charMap = useMemo(() => {
        const map = new Map<string, CharacterInfo>();
        for (const c of characters) map.set(c.name, c);
        return map;
    }, [characters]);

    // 선택된 인물 (기본: 처음 3명)
    const [selected, setSelected] = useState<Set<string>>(new Set());
    useEffect(() => {
        if (isOpen && allNames.length > 0 && selected.size === 0) {
            setSelected(new Set(allNames.slice(0, Math.min(3, allNames.length))));
        }
    }, [isOpen, allNames]);

    // 선택된 인물 기반 필터링된 관계
    const filteredRels = useMemo(() => {
        if (selected.size === 0) return [];
        return relationships.filter(r => selected.has(getSrc(r)) && selected.has(getTgt(r)));
    }, [relationships, selected]);

    // 선택된 인물 기반 필터링된 이름
    const filteredNames = useMemo(() => Array.from(selected), [selected]);

    const toggleChar = (name: string) => {
        setSelected(prev => {
            const next = new Set(prev);
            if (next.has(name)) next.delete(name);
            else next.add(name);
            return next;
        });
    };

    const selectAll = () => setSelected(new Set(allNames));
    const selectNone = () => setSelected(new Set());

    // 캔버스 크기 측정
    useEffect(() => {
        if (!isOpen || !containerRef.current) return;
        const measure = () => {
            if (!containerRef.current) return;
            const rect = containerRef.current.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                setCanvasSize({ w: rect.width, h: rect.height });
            }
        };
        requestAnimationFrame(measure);
        const timer = setTimeout(measure, 100);
        const observer = new ResizeObserver(measure);
        observer.observe(containerRef.current);
        return () => { clearTimeout(timer); observer.disconnect(); };
    }, [isOpen]);

    // 노드 배치 (선택된 인물만)
    useEffect(() => {
        if (!isOpen) return;
        const { w, h } = canvasSize;
        const cx = w / 2;
        const cy = h / 2;
        const count = filteredNames.length;
        const radius = Math.min(w, h) * 0.32;

        nodesRef.current = filteredNames.map((name, i) => {
            const angle = (2 * Math.PI * i) / count - Math.PI / 2;
            return {
                name,
                x: count === 1 ? cx : cx + radius * Math.cos(angle),
                y: count === 1 ? cy : cy + radius * Math.sin(angle),
                color: colorMap.get(name) || '#4F46E5',
                initials: name.slice(0, 2),
            };
        });
    }, [isOpen, filteredNames, canvasSize, colorMap]);

    const getNode = useCallback((name: string) => nodesRef.current.find(n => n.name === name), []);

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

        if (filteredNames.length === 0) {
            ctx.font = '14px Pretendard, "Noto Sans KR", sans-serif';
            ctx.fillStyle = '#999';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('왼쪽에서 인물을 선택하세요', w / 2, h / 2);
            return;
        }

        const nodeR = Math.max(30, Math.min(45, w / (filteredNames.length * 2.2)));

        // 엣지
        for (const rel of filteredRels) {
            const src = getNode(getSrc(rel));
            const tgt = getNode(getTgt(rel));
            if (!src || !tgt) continue;

            const isHL = hoveredNode === src.name || hoveredNode === tgt.name;

            // 선
            ctx.beginPath();
            ctx.moveTo(src.x, src.y);
            ctx.lineTo(tgt.x, tgt.y);
            ctx.strokeStyle = isHL ? src.color : 'rgba(120,120,120,0.4)';
            ctx.lineWidth = isHL ? 3 : 1.8;
            ctx.setLineDash([]);
            ctx.stroke();

            // 화살표 (중앙 방향)
            const mx = (src.x + tgt.x) / 2;
            const my = (src.y + tgt.y) / 2;
            const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
            const arrowLen = 8;
            ctx.beginPath();
            ctx.moveTo(mx + arrowLen * Math.cos(angle), my + arrowLen * Math.sin(angle));
            ctx.lineTo(mx - arrowLen * Math.cos(angle - 0.4), my - arrowLen * Math.sin(angle - 0.4));
            ctx.lineTo(mx - arrowLen * Math.cos(angle + 0.4), my - arrowLen * Math.sin(angle + 0.4));
            ctx.closePath();
            ctx.fillStyle = isHL ? src.color : 'rgba(120,120,120,0.5)';
            ctx.fill();

            // 관계 라벨
            if (rel.relation) {
                const lx = mx;
                const ly = my - 14;
                const text = rel.relation;
                ctx.font = `${isHL ? 'bold 13' : '11'}px Pretendard, "Noto Sans KR", sans-serif`;
                const tm = ctx.measureText(text);
                const pad = 5;
                ctx.fillStyle = 'rgba(255,255,255,0.92)';
                ctx.beginPath();
                ctx.roundRect(lx - tm.width / 2 - pad, ly - 8 - pad, tm.width + pad * 2, 16 + pad * 2, 6);
                ctx.fill();
                ctx.strokeStyle = isHL ? src.color : 'rgba(150,150,150,0.3)';
                ctx.lineWidth = 1;
                ctx.stroke();
                ctx.fillStyle = isHL ? src.color : '#555';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, lx, ly);
            }
        }

        // 노드
        for (const node of nodesRef.current) {
            const isHL = hoveredNode === node.name;
            const r = isHL ? nodeR + 5 : nodeR;

            // 그림자
            ctx.shadowColor = isHL ? `${node.color}55` : 'rgba(0,0,0,0.1)';
            ctx.shadowBlur = isHL ? 20 : 8;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 3;

            // 외곽 글로우
            if (isHL) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 5, 0, Math.PI * 2);
                ctx.fillStyle = `${node.color}20`;
                ctx.fill();
            }

            // 원
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
            ctx.fillStyle = node.color;
            ctx.fill();
            ctx.shadowColor = 'transparent';

            // 테두리
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 3;
            ctx.stroke();

            // 이니셜
            ctx.font = `bold ${Math.round(r * 0.55)}px Pretendard, "Noto Sans KR", sans-serif`;
            ctx.fillStyle = '#fff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(node.initials, node.x, node.y);

            // 이름
            ctx.font = `${isHL ? 'bold ' : ''}13px Pretendard, "Noto Sans KR", sans-serif`;
            ctx.fillStyle = '#333';
            ctx.textBaseline = 'top';
            ctx.fillText(node.name, node.x, node.y + r + 10);
        }
    }, [filteredRels, filteredNames, hoveredNode, canvasSize, getNode]);

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
        const nodeR = Math.max(30, Math.min(45, canvasSize.w / (filteredNames.length * 2.2)));
        let found: string | null = null;
        for (const node of nodesRef.current) {
            const dx = mx - node.x, dy = my - node.y;
            if (dx * dx + dy * dy < (nodeR + 12) * (nodeR + 12)) { found = node.name; break; }
        }
        setHoveredNode(found);
    }, [canvasSize, filteredNames]);

    if (!isOpen) return null;

    // 호버된 인물의 관계 정보
    const hoveredInfo = hoveredNode ? charMap.get(hoveredNode) : null;
    const hoveredRels = hoveredNode ? filteredRels.filter(r => getSrc(r) === hoveredNode || getTgt(r) === hoveredNode) : [];

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 1100,
            background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
            <div style={{
                width: '92vw', maxWidth: '1200px', height: '82vh', maxHeight: '800px',
                background: 'var(--modal-bg, #fff)', borderRadius: '16px',
                border: '1px solid var(--modal-border, #e5e7eb)',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
                display: 'flex', flexDirection: 'column', overflow: 'hidden'
            }}>
                {/* 헤더 */}
                <div style={{
                    padding: '14px 24px', borderBottom: '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'var(--modal-header-bg)', color: 'var(--modal-header-text)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Network size={22} />
                        <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>인물 관계도</h2>
                        <span style={{ fontSize: '0.78rem', opacity: 0.6 }}>
                            {selected.size}/{allNames.length}명 선택 · {filteredRels.length}개 관계
                        </span>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'currentColor', padding: '4px'
                    }}><X size={22} /></button>
                </div>

                {/* 본체 */}
                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    {/* 왼쪽: 인물 선택 패널 */}
                    <div style={{
                        width: '220px', borderRight: '1px solid var(--border)',
                        display: 'flex', flexDirection: 'column', background: 'var(--card-bg, #fafafa)'
                    }}>
                        <div style={{
                            padding: '10px 14px', borderBottom: '1px solid var(--border)',
                            display: 'flex', gap: '6px'
                        }}>
                            <button onClick={selectAll} style={{
                                flex: 1, padding: '5px', fontSize: '0.75rem', fontWeight: 600,
                                border: '1px solid var(--border)', borderRadius: '6px',
                                cursor: 'pointer', background: 'transparent',
                                color: 'var(--foreground)'
                            }}>전체 선택</button>
                            <button onClick={selectNone} style={{
                                flex: 1, padding: '5px', fontSize: '0.75rem', fontWeight: 600,
                                border: '1px solid var(--border)', borderRadius: '6px',
                                cursor: 'pointer', background: 'transparent',
                                color: 'var(--foreground)'
                            }}>선택 해제</button>
                        </div>
                        <div style={{ flex: 1, overflowY: 'auto', padding: '6px' }}>
                            {allNames.map(name => {
                                const isOn = selected.has(name);
                                const color = colorMap.get(name) || '#4F46E5';
                                const info = charMap.get(name);
                                // 이 인물이 관여된 관계 수
                                const relCount = relationships.filter(r => getSrc(r) === name || getTgt(r) === name).length;
                                return (
                                    <button
                                        key={name}
                                        onClick={() => toggleChar(name)}
                                        style={{
                                            width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                                            padding: '8px 10px', marginBottom: '2px', borderRadius: '8px',
                                            border: 'none', cursor: 'pointer', textAlign: 'left',
                                            background: isOn ? `${color}12` : 'transparent',
                                            transition: 'background 0.15s'
                                        }}
                                    >
                                        {/* 체크 원 */}
                                        <div style={{
                                            width: '30px', height: '30px', borderRadius: '50%',
                                            background: isOn ? color : '#ddd', flexShrink: 0,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            color: '#fff', fontSize: '0.7rem', fontWeight: 700,
                                            transition: 'background 0.15s'
                                        }}>
                                            {isOn ? <Check size={14} strokeWidth={3} /> : name.slice(0, 1)}
                                        </div>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{
                                                fontSize: '0.85rem', fontWeight: isOn ? 700 : 500,
                                                color: isOn ? color : 'var(--foreground)',
                                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                                            }}>{name}</div>
                                            <div style={{
                                                fontSize: '0.7rem', color: 'var(--muted-foreground)',
                                                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                                            }}>
                                                {relCount}개 관계{info?.traits?.[0] ? ` · ${info.traits[0]}` : ''}
                                            </div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* 중앙: 그래프 Canvas */}
                    <div ref={containerRef} style={{ flex: 1, position: 'relative', minHeight: 0 }}>
                        <canvas
                            ref={canvasRef}
                            style={{ width: '100%', height: '100%', cursor: hoveredNode ? 'pointer' : 'default' }}
                            onMouseMove={handleMouseMove}
                            onMouseLeave={() => setHoveredNode(null)}
                        />
                        {/* 호버 정보 카드 */}
                        {hoveredNode && (
                            <div style={{
                                position: 'absolute', bottom: '16px', left: '16px',
                                maxWidth: '350px', background: 'var(--modal-bg, #fff)',
                                border: '1px solid var(--border)', borderRadius: '12px',
                                padding: '14px 18px', boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                                pointerEvents: 'none'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                                    <div style={{
                                        width: '28px', height: '28px', borderRadius: '50%',
                                        background: colorMap.get(hoveredNode) || '#4F46E5',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        color: '#fff', fontSize: '0.7rem', fontWeight: 700
                                    }}>{hoveredNode.slice(0, 2)}</div>
                                    <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{hoveredNode}</span>
                                </div>
                                {hoveredInfo?.description && (
                                    <p style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)', margin: '0 0 6px', lineHeight: 1.4 }}>
                                        {hoveredInfo.description.length > 80 ? hoveredInfo.description.slice(0, 80) + '...' : hoveredInfo.description}
                                    </p>
                                )}
                                {hoveredRels.length > 0 && (
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                        {hoveredRels.map((r, i) => {
                                            const other = getSrc(r) === hoveredNode ? getTgt(r) : getSrc(r);
                                            return (
                                                <span key={i} style={{
                                                    fontSize: '0.7rem', padding: '2px 8px', borderRadius: '10px',
                                                    background: `${colorMap.get(other) || '#666'}22`,
                                                    color: colorMap.get(other) || '#666', fontWeight: 600
                                                }}>
                                                    {other}: {r.relation || '관계'}
                                                </span>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
