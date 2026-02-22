import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { X, Network, Check, Users, AlertCircle } from 'lucide-react';

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
    appearance_count?: number;
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
    radius: number;
}

function getSrc(r: Relationship) { return r.source || r.character1 || ''; }
function getTgt(r: Relationship) { return r.target || r.character2 || ''; }

/** CSS 변수에서 색상 읽기 (테마 대응) */
function getThemeColors() {
    const style = getComputedStyle(document.documentElement);
    return {
        foreground: style.getPropertyValue('--foreground').trim() || '#1c1917',
        mutedForeground: style.getPropertyValue('--muted-foreground').trim() || '#78716c',
        modalBg: style.getPropertyValue('--modal-bg').trim() || '#ffffff',
        border: style.getPropertyValue('--border').trim() || '#e7e5e4',
        modalText: style.getPropertyValue('--modal-text').trim() || '#1c1917',
    };
}

export function RelationshipGraphModal({ isOpen, onClose, relationships, characters = [] }: RelationshipGraphModalProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const [canvasSize, setCanvasSize] = useState({ w: 600, h: 500 });
    const nodesRef = useRef<NodeData[]>([]);
    const animFrameRef = useRef<number>(0);

    // 드래그 상태
    const dragRef = useRef<{ name: string; offsetX: number; offsetY: number } | null>(null);
    const [isDragging, setIsDragging] = useState(false);

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

    // appearance_count 범위 계산 (노드 크기 차별화용)
    const appearanceRange = useMemo(() => {
        let min = Infinity, max = 0;
        for (const c of characters) {
            const count = c.appearance_count || 0;
            if (count < min) min = count;
            if (count > max) max = count;
        }
        if (min === Infinity) min = 0;
        return { min, max };
    }, [characters]);

    // 인물별 관계 수
    const relCountMap = useMemo(() => {
        const map = new Map<string, number>();
        for (const r of relationships) {
            const s = getSrc(r), t = getTgt(r);
            map.set(s, (map.get(s) || 0) + 1);
            map.set(t, (map.get(t) || 0) + 1);
        }
        return map;
    }, [relationships]);

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

    // 노드 반경 계산 (appearance_count 기반)
    const getNodeRadius = useCallback((name: string, baseR: number): number => {
        const info = charMap.get(name);
        const count = info?.appearance_count || 0;
        const { min, max } = appearanceRange;
        if (max === min || max === 0) return baseR;
        const ratio = (count - min) / (max - min);
        const minR = baseR * 0.75;
        const maxR = baseR * 1.4;
        return minR + ratio * (maxR - minR);
    }, [charMap, appearanceRange]);

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
        const baseR = Math.max(30, Math.min(45, w / (count * 2.2)));

        nodesRef.current = filteredNames.map((name, i) => {
            const angle = (2 * Math.PI * i) / count - Math.PI / 2;
            return {
                name,
                x: count === 1 ? cx : cx + radius * Math.cos(angle),
                y: count === 1 ? cy : cy + radius * Math.sin(angle),
                color: colorMap.get(name) || '#4F46E5',
                initials: name.slice(0, 2),
                radius: getNodeRadius(name, baseR),
            };
        });
    }, [isOpen, filteredNames, canvasSize, colorMap, getNodeRadius]);

    const getNode = useCallback((name: string) => nodesRef.current.find(n => n.name === name), []);

    // 엣지 두께 계산 (관계 강도 기반)
    const getEdgeWidth = useCallback((rel: Relationship, isHL: boolean): number => {
        if (isHL) return 3.5;
        const descLen = rel.description?.length || 0;
        const srcCount = charMap.get(getSrc(rel))?.appearance_count || 0;
        const tgtCount = charMap.get(getTgt(rel))?.appearance_count || 0;
        const strength = descLen + (srcCount + tgtCount) * 2;
        if (strength > 100) return 3;
        if (strength > 40) return 2.2;
        return 1.5;
    }, [charMap]);

    // 같은 노드 쌍 간 다중 관계 인덱싱
    const edgeIndexMap = useMemo(() => {
        const map = new Map<string, { total: number; current: number }>();
        for (const rel of filteredRels) {
            const key = [getSrc(rel), getTgt(rel)].sort().join('|');
            const entry = map.get(key);
            if (entry) entry.total++;
            else map.set(key, { total: 1, current: 0 });
        }
        return map;
    }, [filteredRels]);

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

        // 테마 색상 가져오기
        const theme = getThemeColors();

        if (filteredNames.length === 0) {
            ctx.font = '14px Pretendard, "Noto Sans KR", sans-serif';
            ctx.fillStyle = theme.mutedForeground;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('왼쪽에서 인물을 선택하세요', w / 2, h / 2);
            return;
        }

        // 다중 엣지 인덱스 리셋
        const edgeCounters = new Map<string, number>();

        // 엣지
        for (const rel of filteredRels) {
            const src = getNode(getSrc(rel));
            const tgt = getNode(getTgt(rel));
            if (!src || !tgt) continue;

            const isHL = hoveredNode === src.name || hoveredNode === tgt.name;
            const edgeWidth = getEdgeWidth(rel, isHL);

            // 다중 관계 오프셋 계산
            const edgeKey = [src.name, tgt.name].sort().join('|');
            const edgeInfo = edgeIndexMap.get(edgeKey);
            const currentIdx = edgeCounters.get(edgeKey) || 0;
            edgeCounters.set(edgeKey, currentIdx + 1);
            const totalEdges = edgeInfo?.total || 1;
            const curveOffset = totalEdges > 1
                ? (currentIdx - (totalEdges - 1) / 2) * 40
                : 0;

            // 선 (직선 또는 곡선)
            const mx = (src.x + tgt.x) / 2;
            const my = (src.y + tgt.y) / 2;
            const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
            const perpX = -Math.sin(angle) * curveOffset;
            const perpY = Math.cos(angle) * curveOffset;
            const cpx = mx + perpX;
            const cpy = my + perpY;

            ctx.beginPath();
            ctx.moveTo(src.x, src.y);
            if (curveOffset !== 0) {
                ctx.quadraticCurveTo(cpx, cpy, tgt.x, tgt.y);
            } else {
                ctx.lineTo(tgt.x, tgt.y);
            }
            ctx.strokeStyle = isHL ? src.color : theme.mutedForeground;
            ctx.lineWidth = edgeWidth;
            ctx.setLineDash([]);
            ctx.stroke();

            // 화살표 (엣지 중앙)
            const arrowX = curveOffset !== 0 ? (src.x + 2 * cpx + tgt.x) / 4 : mx;
            const arrowY = curveOffset !== 0 ? (src.y + 2 * cpy + tgt.y) / 4 : my;
            const arrowAngle = curveOffset !== 0
                ? Math.atan2(tgt.y - src.y + perpY, tgt.x - src.x + perpX)
                : angle;
            const arrowLen = 8;
            ctx.beginPath();
            ctx.moveTo(arrowX + arrowLen * Math.cos(arrowAngle), arrowY + arrowLen * Math.sin(arrowAngle));
            ctx.lineTo(arrowX - arrowLen * Math.cos(arrowAngle - 0.4), arrowY - arrowLen * Math.sin(arrowAngle - 0.4));
            ctx.lineTo(arrowX - arrowLen * Math.cos(arrowAngle + 0.4), arrowY - arrowLen * Math.sin(arrowAngle + 0.4));
            ctx.closePath();
            ctx.fillStyle = isHL ? src.color : theme.mutedForeground;
            ctx.fill();

            // 관계 라벨
            if (rel.relation) {
                const lx = curveOffset !== 0 ? cpx : mx;
                const ly = (curveOffset !== 0 ? cpy : my) - 14;
                const text = rel.relation;
                ctx.font = `${isHL ? 'bold 13' : '11'}px Pretendard, "Noto Sans KR", sans-serif`;
                const tm = ctx.measureText(text);
                const pad = 5;
                ctx.fillStyle = `${theme.modalBg}ee`;
                ctx.beginPath();
                ctx.roundRect(lx - tm.width / 2 - pad, ly - 8 - pad, tm.width + pad * 2, 16 + pad * 2, 6);
                ctx.fill();
                ctx.strokeStyle = isHL ? src.color : `${theme.border}`;
                ctx.lineWidth = 1;
                ctx.stroke();
                ctx.fillStyle = isHL ? src.color : theme.mutedForeground;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, lx, ly);
            }
        }

        // 노드
        for (const node of nodesRef.current) {
            const isHL = hoveredNode === node.name;
            const r = isHL ? node.radius + 5 : node.radius;

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
            ctx.strokeStyle = theme.modalBg;
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
            ctx.fillStyle = theme.foreground;
            ctx.textBaseline = 'top';
            ctx.fillText(node.name, node.x, node.y + r + 10);
        }
    }, [filteredRels, filteredNames, hoveredNode, canvasSize, getNode, getEdgeWidth, edgeIndexMap]);

    useEffect(() => {
        if (!isOpen) return;
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = requestAnimationFrame(draw);
    }, [draw, isOpen]);

    // 마우스 좌표 → 캔버스 좌표 변환
    const getCanvasXY = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return { mx: 0, my: 0 };
        const rect = canvas.getBoundingClientRect();
        return { mx: e.clientX - rect.left, my: e.clientY - rect.top };
    }, []);

    // 노드 히트 테스트
    const hitTest = useCallback((mx: number, my: number): NodeData | null => {
        for (const node of nodesRef.current) {
            const dx = mx - node.x, dy = my - node.y;
            if (dx * dx + dy * dy < (node.radius + 12) * (node.radius + 12)) return node;
        }
        return null;
    }, []);

    // mousedown: 드래그 시작
    const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const { mx, my } = getCanvasXY(e);
        const node = hitTest(mx, my);
        if (node) {
            dragRef.current = { name: node.name, offsetX: mx - node.x, offsetY: my - node.y };
            setIsDragging(true);
        }
    }, [getCanvasXY, hitTest]);

    // mousemove: 드래그 중이면 노드 이동, 아니면 호버
    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const { mx, my } = getCanvasXY(e);

        if (dragRef.current) {
            const node = nodesRef.current.find(n => n.name === dragRef.current!.name);
            if (node) {
                node.x = mx - dragRef.current.offsetX;
                node.y = my - dragRef.current.offsetY;
                cancelAnimationFrame(animFrameRef.current);
                animFrameRef.current = requestAnimationFrame(draw);
            }
            return;
        }

        const found = hitTest(mx, my);
        setHoveredNode(found?.name || null);
    }, [getCanvasXY, hitTest, draw]);

    // mouseup: 드래그 종료
    const handleMouseUp = useCallback(() => {
        dragRef.current = null;
        setIsDragging(false);
    }, []);

    // mouseleave: 드래그 & 호버 종료
    const handleMouseLeave = useCallback(() => {
        dragRef.current = null;
        setIsDragging(false);
        setHoveredNode(null);
    }, []);

    if (!isOpen) return null;

    // 호버된 인물의 관계 정보
    const hoveredInfo = hoveredNode ? charMap.get(hoveredNode) : null;
    const hoveredRels = hoveredNode ? filteredRels.filter(r => getSrc(r) === hoveredNode || getTgt(r) === hoveredNode) : [];
    const hoveredRelCount = hoveredNode ? (relCountMap.get(hoveredNode) || 0) : 0;

    // 커서 스타일
    const cursorStyle = isDragging ? 'grabbing' : hoveredNode ? 'grab' : 'default';

    // 빈 데이터 상태
    const hasNoData = allNames.length === 0;
    const hasNoRelationships = allNames.length > 0 && relationships.length === 0;

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

                {/* 빈 데이터 상태 */}
                {hasNoData ? (
                    <div style={{
                        flex: 1, display: 'flex', flexDirection: 'column',
                        alignItems: 'center', justifyContent: 'center', gap: '16px',
                        color: 'var(--muted-foreground)', padding: '40px'
                    }}>
                        <AlertCircle size={48} strokeWidth={1.5} />
                        <div style={{ textAlign: 'center' }}>
                            <p style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 8px' }}>
                                분석 데이터가 없습니다
                            </p>
                            <p style={{ fontSize: '0.85rem', opacity: 0.7, margin: 0 }}>
                                스토리보드 분석을 먼저 실행해주세요.
                            </p>
                        </div>
                    </div>
                ) : hasNoRelationships ? (
                    <div style={{
                        flex: 1, display: 'flex', flexDirection: 'column',
                        alignItems: 'center', justifyContent: 'center', gap: '16px',
                        color: 'var(--muted-foreground)', padding: '40px'
                    }}>
                        <Users size={48} strokeWidth={1.5} />
                        <div style={{ textAlign: 'center' }}>
                            <p style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 8px' }}>
                                인물 간 관계 데이터가 없습니다
                            </p>
                            <p style={{ fontSize: '0.85rem', opacity: 0.7, margin: 0 }}>
                                {allNames.length}명의 인물이 감지되었지만 관계 정보가 아직 분석되지 않았습니다.
                            </p>
                        </div>
                    </div>
                ) : (
                    /* 본체 */
                    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                        {/* 왼쪽: 인물 선택 패널 */}
                        <div style={{
                            width: '220px', borderRight: '1px solid var(--border)',
                            display: 'flex', flexDirection: 'column',
                            background: (() => {
                                const t = document.documentElement.getAttribute('data-theme') || 'light';
                                return t === 'dark' ? '#0a0a0a' : t === 'sepia' ? '#fdf6e3' : '#fafafa';
                            })()
                        }}>
                            <div style={{
                                padding: '10px 14px', borderBottom: '1px solid var(--border)',
                                display: 'flex', gap: '6px'
                            }}>
                                <button onClick={selectAll} style={{
                                    flex: 1, padding: '5px', fontSize: '0.75rem', fontWeight: 600,
                                    border: '1px solid var(--border)', borderRadius: '6px',
                                    cursor: 'pointer', color: 'var(--foreground)',
                                    background: (() => {
                                        const t = document.documentElement.getAttribute('data-theme') || 'light';
                                        return t === 'dark' ? '#333333' : t === 'sepia' ? '#e6d3c1' : 'transparent';
                                    })()
                                }}>전체 선택</button>
                                <button onClick={selectNone} style={{
                                    flex: 1, padding: '5px', fontSize: '0.75rem', fontWeight: 600,
                                    border: '1px solid var(--border)', borderRadius: '6px',
                                    cursor: 'pointer', color: 'var(--foreground)',
                                    background: (() => {
                                        const t = document.documentElement.getAttribute('data-theme') || 'light';
                                        return t === 'dark' ? '#333333' : t === 'sepia' ? '#e6d3c1' : 'transparent';
                                    })()
                                }}>선택 해제</button>
                            </div>
                            <div style={{ flex: 1, overflowY: 'auto', padding: '6px' }}>
                                {allNames.map(name => {
                                    const isOn = selected.has(name);
                                    const color = colorMap.get(name) || '#4F46E5';
                                    const info = charMap.get(name);
                                    const relCount = relCountMap.get(name) || 0;
                                    const appCount = info?.appearance_count;
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
                                                    {relCount}개 관계{appCount ? ` · ${appCount}회 등장` : ''}{info?.traits?.[0] ? ` · ${info.traits[0]}` : ''}
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
                                style={{ width: '100%', height: '100%', cursor: cursorStyle }}
                                onMouseDown={handleMouseDown}
                                onMouseMove={handleMouseMove}
                                onMouseUp={handleMouseUp}
                                onMouseLeave={handleMouseLeave}
                            />
                            {/* 호버 정보 카드 */}
                            {hoveredNode && !isDragging && (
                                <div style={{
                                    position: 'absolute', bottom: '16px', left: '16px',
                                    maxWidth: '380px', background: 'var(--modal-bg, #fff)',
                                    border: '1px solid var(--border)', borderRadius: '12px',
                                    padding: '14px 18px', boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                                    pointerEvents: 'none', color: 'var(--modal-text, #1c1917)'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                                        <div style={{
                                            width: '28px', height: '28px', borderRadius: '50%',
                                            background: colorMap.get(hoveredNode) || '#4F46E5',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            color: '#fff', fontSize: '0.7rem', fontWeight: 700
                                        }}>{hoveredNode.slice(0, 2)}</div>
                                        <div>
                                            <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{hoveredNode}</span>
                                            <div style={{ fontSize: '0.72rem', color: 'var(--muted-foreground)', marginTop: '1px' }}>
                                                {hoveredRelCount}개 관계
                                                {hoveredInfo?.appearance_count ? ` · ${hoveredInfo.appearance_count}회 등장` : ''}
                                            </div>
                                        </div>
                                    </div>
                                    {/* traits 태그 */}
                                    {hoveredInfo?.traits && hoveredInfo.traits.length > 0 && (
                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '8px' }}>
                                            {hoveredInfo.traits.map((trait, i) => (
                                                <span key={i} style={{
                                                    fontSize: '0.68rem', padding: '2px 8px', borderRadius: '10px',
                                                    background: `${colorMap.get(hoveredNode) || '#4F46E5'}18`,
                                                    color: colorMap.get(hoveredNode) || '#4F46E5',
                                                    fontWeight: 600, border: `1px solid ${colorMap.get(hoveredNode) || '#4F46E5'}30`
                                                }}>
                                                    {trait}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                    {hoveredInfo?.description && (
                                        <p style={{
                                            fontSize: '0.8rem', color: 'var(--muted-foreground)',
                                            margin: '0 0 8px', lineHeight: 1.5
                                        }}>
                                            {hoveredInfo.description.length > 150 ? hoveredInfo.description.slice(0, 150) + '...' : hoveredInfo.description}
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
                )}
            </div>
        </div>
    );
}
