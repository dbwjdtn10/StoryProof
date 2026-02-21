import { useState, useRef, useEffect, useCallback } from 'react';

interface Relationship {
    character1?: string;
    character2?: string;
    source?: string;
    target?: string;
    relation?: string;
    description?: string;
}

interface CharacterNode {
    name: string;
    x: number;
    y: number;
    color: string;
}

interface RelationshipGraphProps {
    relationships: Relationship[];
    characters?: string[];
    width?: number;
    height?: number;
}

const NODE_COLORS = [
    '#4F46E5', '#DC2626', '#059669', '#D97706', '#7C3AED',
    '#DB2777', '#0891B2', '#65A30D', '#EA580C', '#6366F1',
    '#14B8A6', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899',
];

export function RelationshipGraph({ relationships, characters = [], width = 500, height = 400 }: RelationshipGraphProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);
    const [hoveredEdge, setHoveredEdge] = useState<number | null>(null);
    const nodesRef = useRef<CharacterNode[]>([]);

    // 관계에서 모든 캐릭터 이름 추출
    const allNames = useRef<string[]>([]);
    useEffect(() => {
        const nameSet = new Set<string>();
        for (const c of characters) nameSet.add(c);
        for (const r of relationships) {
            const src = r.source || r.character1 || '';
            const tgt = r.target || r.character2 || '';
            if (src) nameSet.add(src);
            if (tgt) nameSet.add(tgt);
        }
        allNames.current = Array.from(nameSet);

        // 원형 배치
        const cx = width / 2;
        const cy = height / 2;
        const radius = Math.min(width, height) * 0.35;
        const count = allNames.current.length;
        nodesRef.current = allNames.current.map((name, i) => ({
            name,
            x: cx + radius * Math.cos((2 * Math.PI * i) / count - Math.PI / 2),
            y: cy + radius * Math.sin((2 * Math.PI * i) / count - Math.PI / 2),
            color: NODE_COLORS[i % NODE_COLORS.length],
        }));
    }, [relationships, characters, width, height]);

    const getNode = useCallback((name: string) => {
        return nodesRef.current.find(n => n.name === name);
    }, []);

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);

        // 배경
        ctx.clearRect(0, 0, width, height);

        // 엣지 그리기
        relationships.forEach((rel, idx) => {
            const src = getNode(rel.source || rel.character1 || '');
            const tgt = getNode(rel.target || rel.character2 || '');
            if (!src || !tgt) return;

            const isHovered = hoveredEdge === idx ||
                hoveredNode === src.name || hoveredNode === tgt.name;

            ctx.beginPath();
            ctx.moveTo(src.x, src.y);
            ctx.lineTo(tgt.x, tgt.y);
            ctx.strokeStyle = isHovered ? '#4F46E5' : 'rgba(150,150,150,0.4)';
            ctx.lineWidth = isHovered ? 2.5 : 1.2;
            ctx.stroke();

            // 관계 라벨
            if (rel.relation) {
                const mx = (src.x + tgt.x) / 2;
                const my = (src.y + tgt.y) / 2;
                ctx.font = `${isHovered ? 'bold ' : ''}11px Pretendard, sans-serif`;
                ctx.fillStyle = isHovered ? '#4F46E5' : '#888';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                // 라벨 배경
                const text = rel.relation;
                const tm = ctx.measureText(text);
                const pad = 3;
                ctx.fillStyle = 'rgba(255,255,255,0.85)';
                ctx.fillRect(mx - tm.width / 2 - pad, my - 7 - pad, tm.width + pad * 2, 14 + pad * 2);
                ctx.fillStyle = isHovered ? '#4F46E5' : '#666';
                ctx.fillText(text, mx, my);
            }
        });

        // 노드 그리기
        for (const node of nodesRef.current) {
            const isHovered = hoveredNode === node.name;
            const nodeRadius = isHovered ? 22 : 18;

            // 그림자
            ctx.shadowColor = isHovered ? 'rgba(79,70,229,0.3)' : 'rgba(0,0,0,0.1)';
            ctx.shadowBlur = isHovered ? 12 : 4;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 2;

            ctx.beginPath();
            ctx.arc(node.x, node.y, nodeRadius, 0, Math.PI * 2);
            ctx.fillStyle = node.color;
            ctx.fill();
            ctx.shadowColor = 'transparent';

            // 이름 라벨
            ctx.font = `bold 12px Pretendard, sans-serif`;
            ctx.fillStyle = '#333';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(node.name, node.x, node.y + nodeRadius + 4);
        }
    }, [relationships, hoveredNode, hoveredEdge, width, height, getNode]);

    useEffect(() => {
        draw();
    }, [draw]);

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        // 노드 히트 테스트
        let foundNode: string | null = null;
        for (const node of nodesRef.current) {
            const dx = mx - node.x;
            const dy = my - node.y;
            if (dx * dx + dy * dy < 22 * 22) {
                foundNode = node.name;
                break;
            }
        }
        setHoveredNode(foundNode);

        // 엣지 히트 테스트
        if (!foundNode) {
            let foundEdge: number | null = null;
            for (let i = 0; i < relationships.length; i++) {
                const rel = relationships[i];
                const src = getNode(rel.source || rel.character1 || '');
                const tgt = getNode(rel.target || rel.character2 || '');
                if (!src || !tgt) continue;
                const dist = pointToSegmentDist(mx, my, src.x, src.y, tgt.x, tgt.y);
                if (dist < 8) {
                    foundEdge = i;
                    break;
                }
            }
            setHoveredEdge(foundEdge);
        } else {
            setHoveredEdge(null);
        }
    }, [relationships, getNode]);

    if (relationships.length === 0) {
        return <div style={{ textAlign: 'center', color: 'var(--muted-foreground)', padding: '2rem', fontSize: '0.85rem' }}>관계 데이터가 없습니다.</div>;
    }

    return (
        <div style={{ position: 'relative' }}>
            <canvas
                ref={canvasRef}
                style={{ width: `${width}px`, height: `${height}px`, cursor: hoveredNode ? 'pointer' : 'default' }}
                onMouseMove={handleMouseMove}
                onMouseLeave={() => { setHoveredNode(null); setHoveredEdge(null); }}
            />
            {hoveredEdge !== null && relationships[hoveredEdge]?.description && (
                <div style={{
                    position: 'absolute', bottom: '8px', left: '8px', right: '8px',
                    background: 'var(--card-bg, #fff)', border: '1px solid var(--border)',
                    borderRadius: '8px', padding: '8px 12px', fontSize: '0.8rem',
                    color: 'var(--foreground)', boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                }}>
                    <strong>{relationships[hoveredEdge].source || relationships[hoveredEdge].character1}</strong>
                    {' → '}
                    <strong>{relationships[hoveredEdge].target || relationships[hoveredEdge].character2}</strong>
                    {': '}{relationships[hoveredEdge].description}
                </div>
            )}
        </div>
    );
}

function pointToSegmentDist(px: number, py: number, x1: number, y1: number, x2: number, y2: number): number {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}
