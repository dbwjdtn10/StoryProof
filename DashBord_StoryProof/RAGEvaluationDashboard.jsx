import { useState } from "react";
import {
  LineChart, Line, BarChart, Bar, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine,
  LabelList
} from "recharts";

// ── Data ──────────────────────────────────────────────────────────────────────

const STAGES = ["RAG 없음", "Dense Only", "+ Hybrid"];

const hitKData = [
  { stage: "RAG 없음",  "Hit@1": 0,    "Hit@3": 0,    "Hit@5": 0    },
  { stage: "Dense Only","Hit@1": 64.9, "Hit@3": 78.7, "Hit@5": 83.1 },
  { stage: "+ Hybrid",  "Hit@1": 89.3, "Hit@3": 96.4, "Hit@5": 96.9 },
];

const acData = [
  { stage: "RAG 없음",   score: 1.72 },
  { stage: "Dense Only", score: 3.72 },
  { stage: "+ Hybrid",   score: 3.81 },
];

const novelData = [
  { name: "톰 소여",     stage0: 1.6, hybrid: 4.2 },
  { name: "보물섬",      stage0: 1.8, hybrid: 3.8 },
  { name: "앨리스",      stage0: 1.5, hybrid: 4.0 },
  { name: "오즈",        stage0: 1.7, hybrid: 3.9 },
  { name: "피터팬",      stage0: 2.0, hybrid: 4.3 },
  { name: "지킬/하이드", stage0: 1.9, hybrid: 4.1 },
  { name: "셜록홈즈",    stage0: 1.8, hybrid: 4.4 },
  { name: "개츠비",      stage0: 1.6, hybrid: 3.7 },
  { name: "오만과편견",  stage0: 2.1, hybrid: 4.0 },
  { name: "타임머신",    stage0: 1.7, hybrid: 4.2 },
  { name: "우주전쟁",    stage0: 1.5, hybrid: 3.6 },
  { name: "삼국지1",     stage0: 1.8, hybrid: 3.9 },
  { name: "삼국지2",     stage0: 1.6, hybrid: 3.5 },
  { name: "삼국지3",     stage0: 1.7, hybrid: 3.8 },
];

const radarData = [
  { metric: "Hit@1",  "RAG 없음": 0,    "Dense Only": 64.9, "+ Hybrid": 89.3 },
  { metric: "Hit@3",  "RAG 없음": 0,    "Dense Only": 78.7, "+ Hybrid": 96.4 },
  { metric: "Hit@5",  "RAG 없음": 0,    "Dense Only": 83.1, "+ Hybrid": 96.9 },
  { metric: "정확도×20","RAG 없음": 34.4, "Dense Only": 74.4, "+ Hybrid": 76.2 },
];

// ── Palette ───────────────────────────────────────────────────────────────────

const C = {
  coral:  "#D85A30",
  amber:  "#EF9F27",
  teal:   "#1D9E75",
  blue:   "#378ADD",
  gray:   "#888780",
  light:  "#F7F5F0",
  border: "#E8E5DF",
  bg:     "#FAFAF8",
  text:   "#1C1C1A",
  muted:  "#7A7870",
};

const STAGE_COLOR = {
  "RAG 없음":   C.coral,
  "Dense Only": C.gray,
  "+ Hybrid":   C.amber,
};

// ── Shared tooltip ────────────────────────────────────────────────────────────

const CustomTooltip = ({ active, payload, label, suffix = "" }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#fff", border: `1px solid ${C.border}`,
      borderRadius: 8, padding: "10px 14px", fontSize: 12,
      boxShadow: "0 4px 16px rgba(0,0,0,0.08)"
    }}>
      <p style={{ margin: "0 0 6px", fontWeight: 600, color: C.text }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ margin: "2px 0", color: p.color }}>
          {p.name}: <strong>{typeof p.value === "number" ? p.value.toFixed(1) : p.value}{suffix}</strong>
        </p>
      ))}
    </div>
  );
};

// ── Metric card ───────────────────────────────────────────────────────────────

const MetricCard = ({ label, value, delta, accent }) => (
  <div style={{
    background: "#fff", border: `1px solid ${C.border}`,
    borderRadius: 12, padding: "18px 20px",
    borderTop: `3px solid ${accent}`,
  }}>
    <p style={{ margin: "0 0 8px", fontSize: 11, color: C.muted, letterSpacing: "0.06em", textTransform: "uppercase" }}>{label}</p>
    <p style={{ margin: "0 0 4px", fontSize: 26, fontWeight: 700, color: C.text, fontFamily: "'DM Mono', monospace" }}>{value}</p>
    <p style={{ margin: 0, fontSize: 11, color: C.teal, fontWeight: 500 }}>{delta}</p>
  </div>
);

// ── Section header ─────────────────────────────────────────────────────────────

const SectionHeader = ({ title, sub }) => (
  <div style={{ marginBottom: 16 }}>
    <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: C.text }}>{title}</h3>
    {sub && <p style={{ margin: "3px 0 0", fontSize: 12, color: C.muted }}>{sub}</p>}
  </div>
);

// ── Legend row ────────────────────────────────────────────────────────────────

const LegendRow = ({ items }) => (
  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 10 }}>
    {items.map(({ color, label }) => (
      <span key={label} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: C.muted }}>
        <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: "inline-block" }} />
        {label}
      </span>
    ))}
  </div>
);

// ── Tab selector ──────────────────────────────────────────────────────────────

const Tabs = ({ tabs, active, onChange }) => (
  <div style={{ display: "flex", gap: 4, marginBottom: 20 }}>
    {tabs.map((t) => (
      <button
        key={t}
        onClick={() => onChange(t)}
        style={{
          padding: "6px 14px", fontSize: 12, borderRadius: 20,
          border: `1px solid ${active === t ? C.amber : C.border}`,
          background: active === t ? C.amber : "transparent",
          color: active === t ? "#fff" : C.muted,
          cursor: "pointer", fontWeight: active === t ? 600 : 400,
          transition: "all 0.18s",
        }}
      >
        {t}
      </button>
    ))}
  </div>
);

// ── Progress bar ──────────────────────────────────────────────────────────────

const ProgressBar = ({ label, value, color, max = 100 }) => (
  <div style={{ marginBottom: 10 }}>
    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
      <span style={{ fontSize: 11, color: C.muted }}>{label}</span>
      <span style={{ fontSize: 11, fontWeight: 600, color: C.text }}>{value.toFixed(1)}%</span>
    </div>
    <div style={{ background: C.light, borderRadius: 4, height: 6, overflow: "hidden" }}>
      <div style={{
        width: `${(value / max) * 100}%`, height: "100%",
        background: color, borderRadius: 4,
        transition: "width 0.6s cubic-bezier(.4,0,.2,1)"
      }} />
    </div>
  </div>
);

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function RAGDashboard() {
  const [activeTab, setActiveTab] = useState("검색 품질 (Hit@K)");
  const [hoveredNovel, setHoveredNovel] = useState(null);

  const card = {
    background: "#fff", border: `1px solid ${C.border}`,
    borderRadius: 12, padding: "20px 22px",
  };

  return (
    <div style={{
      fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
      background: C.bg, minHeight: "100vh", padding: "32px 28px",
      color: C.text, maxWidth: 1100, margin: "0 auto",
    }}>

      {/* ── Header ── */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 6, height: 28, background: C.amber, borderRadius: 3 }} />
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: C.text }}>
            RAG 파이프라인 평가 대시보드
          </h1>
        </div>
        <p style={{ margin: "0 0 0 16px", fontSize: 13, color: C.muted }}>
          14개 소설 · 3단계 비교 — Dense + BM25 Hybrid (α=0.7) · LLM-as-Judge 평가
        </p>
      </div>

      {/* ── Metric Cards ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 28 }}>
        <MetricCard label="Hit@1 최종" value="89.3%" delta="↑ +89.3pp vs 기준" accent={C.coral} />
        <MetricCard label="Hit@5 최종" value="96.9%" delta="↑ +96.9pp vs 기준" accent={C.amber} />
        <MetricCard label="Answer Correctness" value="3.81 / 5" delta="↑ +2.09점 vs Stage 0" accent={C.teal} />
        <MetricCard label="Hybrid 개선폭" value="+24.4pp" delta="Dense → Hybrid Hit@1" accent={C.blue} />
      </div>

      {/* ── Tabs ── */}
      <Tabs
        tabs={["검색 품질 (Hit@K)", "응답 품질 (Correctness)", "소설별 비교", "종합 레이더"]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* ══ TAB 1: Hit@K ══════════════════════════════════════════════════════ */}
      {activeTab === "검색 품질 (Hit@K)" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          {/* Grouped Bar */}
          <div style={card}>
            <SectionHeader title="단계별 Hit@K 비교" sub="RAG 없음 → Dense Only → Hybrid" />
            <LegendRow items={[
              { color: C.coral, label: "Hit@1" },
              { color: C.amber, label: "Hit@3" },
              { color: C.teal,  label: "Hit@5" },
            ]} />
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={hitKData} barGap={3} barCategoryGap="28%">
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                <XAxis dataKey="stage" tick={{ fontSize: 11, fill: C.muted }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false}
                  tickFormatter={v => v + "%"} domain={[0, 105]} />
                <Tooltip content={<CustomTooltip suffix="%" />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
                <Bar dataKey="Hit@1" fill={C.coral} radius={[3, 3, 0, 0]}>
                  <LabelList dataKey="Hit@1" position="top" formatter={v => v > 0 ? v + "%" : ""} style={{ fontSize: 9, fill: C.muted }} />
                </Bar>
                <Bar dataKey="Hit@3" fill={C.amber} radius={[3, 3, 0, 0]}>
                  <LabelList dataKey="Hit@3" position="top" formatter={v => v > 0 ? v + "%" : ""} style={{ fontSize: 9, fill: C.muted }} />
                </Bar>
                <Bar dataKey="Hit@5" fill={C.teal} radius={[3, 3, 0, 0]}>
                  <LabelList dataKey="Hit@5" position="top" formatter={v => v > 0 ? v + "%" : ""} style={{ fontSize: 9, fill: C.muted }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Hit@1 progress per stage */}
          <div style={card}>
            <SectionHeader title="단계별 Hit@K 누적 달성률" sub="검색 성능 개선 경로" />
            {[
              { label: "RAG 없음", color: C.coral },
              { label: "Dense Only", color: C.gray },
              { label: "+ Hybrid ★", color: C.amber },
            ].map(({ label, color }, i) => {
              const d = hitKData[i];
              return (
                <div key={label} style={{
                  background: C.light, borderRadius: 10, padding: "14px 16px",
                  marginBottom: i < 2 ? 10 : 0,
                  borderLeft: `3px solid ${color}`
                }}>
                  <p style={{ margin: "0 0 10px", fontSize: 12, fontWeight: 600, color }}>{label}</p>
                  <ProgressBar label="Hit@1" value={d["Hit@1"]} color={C.coral} />
                  <ProgressBar label="Hit@3" value={d["Hit@3"]} color={C.amber} />
                  <ProgressBar label="Hit@5" value={d["Hit@5"]} color={C.teal} />
                </div>
              );
            })}
          </div>

          {/* Hit@1 line */}
          <div style={{ ...card, gridColumn: "1 / -1" }}>
            <SectionHeader title="Hit@1 단계별 추이" sub="0% → 64.9% → 89.3% 순차 개선" />
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={hitKData}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                <XAxis dataKey="stage" tick={{ fontSize: 11, fill: C.muted }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false}
                  tickFormatter={v => v + "%"} domain={[0, 105]} />
                <Tooltip content={<CustomTooltip suffix="%" />} />
                <ReferenceLine y={89.3} stroke={C.amber} strokeDasharray="4 3" strokeWidth={1.5} label={{ value: "최종 89.3%", fill: C.amber, fontSize: 10, position: "right" }} />
                <Line type="monotone" dataKey="Hit@1" stroke={C.coral} strokeWidth={2.5}
                  dot={{ r: 6, fill: "#fff", stroke: C.coral, strokeWidth: 2.5 }}
                  activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ══ TAB 2: Answer Correctness ════════════════════════════════════════ */}
      {activeTab === "응답 품질 (Correctness)" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          {/* Line chart */}
          <div style={card}>
            <SectionHeader title="Answer Correctness 단계별 추이" sub="LLM-as-Judge 5점 만점 평가" />
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={acData} margin={{ top: 10, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                <XAxis dataKey="stage" tick={{ fontSize: 11, fill: C.muted }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false}
                  domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} />
                <Tooltip content={<CustomTooltip suffix="점" />} />
                <ReferenceLine y={3.81} stroke={C.teal} strokeDasharray="4 3" strokeWidth={1.5}
                  label={{ value: "최종 3.81점", fill: C.teal, fontSize: 10, position: "right" }} />
                <Line type="monotone" dataKey="score" stroke={C.blue} strokeWidth={3}
                  dot={({ cx, cy, index }) => (
                    <circle key={index} cx={cx} cy={cy} r={8} fill="#fff"
                      stroke={[C.coral, C.gray, C.amber][index]} strokeWidth={2.5} />
                  )}
                  activeDot={{ r: 10 }}>
                  <LabelList dataKey="score" position="top" offset={12}
                    formatter={v => v.toFixed(2) + "점"} style={{ fontSize: 11, fontWeight: 600, fill: C.text }} />
                </Line>
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Bar with delta */}
          <div style={card}>
            <SectionHeader title="단계별 Answer Correctness 상세" sub="기준(RAG 없음) 대비 개선량" />
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={acData} barCategoryGap="40%">
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                <XAxis dataKey="stage" tick={{ fontSize: 11, fill: C.muted }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false} domain={[0, 5]} />
                <Tooltip content={<CustomTooltip suffix="점" />} />
                <Bar dataKey="score" radius={[5, 5, 0, 0]}>
                  {acData.map((_, i) => (
                    <Cell key={i} fill={[C.coral, C.gray, C.amber][i]} />
                  ))}
                  <LabelList dataKey="score" position="top" formatter={v => v.toFixed(2)}
                    style={{ fontSize: 12, fontWeight: 700, fill: C.text }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div style={{ marginTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              {[
                { label: "RAG 없음", val: "1.72", delta: "기준", color: C.coral },
                { label: "Dense Only", val: "3.72", delta: "+2.00", color: C.gray },
                { label: "+ Hybrid", val: "3.81", delta: "+2.09", color: C.amber },
              ].map(({ label, val, delta, color }) => (
                <div key={label} style={{ background: C.light, borderRadius: 8, padding: "10px 12px", borderTop: `2px solid ${color}` }}>
                  <p style={{ margin: "0 0 4px", fontSize: 10, color: C.muted }}>{label}</p>
                  <p style={{ margin: 0, fontSize: 18, fontWeight: 700, fontFamily: "monospace", color: C.text }}>{val}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: C.teal, fontWeight: 500 }}>{delta}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ══ TAB 3: 소설별 비교 ══════════════════════════════════════════════ */}
      {activeTab === "소설별 비교" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
          <div style={card}>
            <SectionHeader title="소설별 Answer Correctness — Stage 0 vs Hybrid" sub="14개 소설 전체 비교 (1–5점)" />
            <LegendRow items={[
              { color: C.coral, label: "Stage 0 (RAG 없음)" },
              { color: C.amber, label: "+ Hybrid ★" },
            ]} />
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={novelData} barGap={2} barCategoryGap="25%"
                onMouseMove={e => e.activeLabel && setHoveredNovel(e.activeLabel)}
                onMouseLeave={() => setHoveredNovel(null)}>
                <CartesianGrid strokeDasharray="3 3" stroke={C.border} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 9, fill: C.muted }}
                  axisLine={false} tickLine={false} angle={-30} textAnchor="end" height={52} />
                <YAxis tick={{ fontSize: 10, fill: C.muted }} axisLine={false} tickLine={false}
                  domain={[0, 5]} ticks={[0, 1, 2, 3, 4, 5]} />
                <Tooltip content={<CustomTooltip suffix="점" />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
                <Bar dataKey="stage0" name="Stage 0" fill={C.coral} radius={[3, 3, 0, 0]} />
                <Bar dataKey="hybrid" name="Hybrid" fill={C.amber} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Delta cards */}
          <div style={card}>
            <SectionHeader title="소설별 개선 델타 (Hybrid − Stage 0)" sub="모든 소설에서 +1.7점 이상 향상" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 8 }}>
              {novelData.map(({ name, stage0, hybrid }) => {
                const delta = (hybrid - stage0).toFixed(1);
                const pct = ((hybrid - stage0) / 3) * 100;
                return (
                  <div key={name} style={{
                    background: C.light, borderRadius: 8, padding: "10px 8px",
                    textAlign: "center", borderBottom: `3px solid ${C.amber}`,
                    transition: "transform 0.15s",
                    transform: hoveredNovel === name ? "translateY(-3px)" : "none",
                  }}>
                    <p style={{ margin: "0 0 6px", fontSize: 9, color: C.muted, lineHeight: 1.3 }}>{name}</p>
                    <p style={{ margin: 0, fontSize: 15, fontWeight: 700, color: C.teal, fontFamily: "monospace" }}>+{delta}</p>
                    <div style={{ background: C.border, borderRadius: 2, height: 3, marginTop: 5, overflow: "hidden" }}>
                      <div style={{ width: `${pct}%`, height: "100%", background: C.amber, borderRadius: 2 }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ══ TAB 4: 레이더 ═══════════════════════════════════════════════════ */}
      {activeTab === "종합 레이더" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div style={card}>
            <SectionHeader title="단계별 종합 성능 레이더" sub="Hit@1/3/5 및 정확도(×20 스케일) 비교" />
            <LegendRow items={[
              { color: C.coral, label: "RAG 없음" },
              { color: C.gray,  label: "Dense Only" },
              { color: C.amber, label: "+ Hybrid" },
            ]} />
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
                <PolarGrid stroke={C.border} />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: C.muted }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9, fill: C.muted }} tickCount={4} />
                <Radar name="RAG 없음"   dataKey="RAG 없음"   stroke={C.coral} fill={C.coral} fillOpacity={0.1} strokeWidth={2} />
                <Radar name="Dense Only" dataKey="Dense Only" stroke={C.gray}  fill={C.gray}  fillOpacity={0.1} strokeWidth={2} />
                <Radar name="+ Hybrid"   dataKey="+ Hybrid"   stroke={C.amber} fill={C.amber} fillOpacity={0.2} strokeWidth={2.5} />
                <Tooltip content={<CustomTooltip suffix="%" />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Summary table */}
          <div style={card}>
            <SectionHeader title="단계별 핵심 지표 요약" sub="최종 Hybrid 단계 강조" />
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${C.border}` }}>
                  {["단계", "Hit@1", "Hit@3", "Hit@5", "Correctness"].map(h => (
                    <th key={h} style={{ padding: "8px 10px", textAlign: "left", fontSize: 10, color: C.muted, fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { stage: "RAG 없음",   color: C.coral, h1: "0%",     h3: "0%",     h5: "0%",     ac: "1.72" },
                  { stage: "Dense Only", color: C.gray,  h1: "64.9%",  h3: "78.7%",  h5: "83.1%",  ac: "3.72" },
                  { stage: "+ Hybrid",   color: C.amber, h1: "89.3%",  h3: "96.4%",  h5: "96.9%",  ac: "3.81", highlight: true },
                ].map(({ stage, color, h1, h3, h5, ac, highlight }) => (
                  <tr key={stage} style={{
                    borderBottom: `1px solid ${C.border}`,
                    background: highlight ? "#FFFBF0" : "transparent",
                  }}>
                    <td style={{ padding: "10px 10px" }}>
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 12,
                        background: `${color}18`, color, fontSize: 11, fontWeight: 600
                      }}>{stage}</span>
                    </td>
                    {[h1, h3, h5, ac + "점"].map((v, i) => (
                      <td key={i} style={{ padding: "10px 10px", fontWeight: highlight ? 700 : 400, color: highlight ? C.text : C.muted }}>{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ marginTop: 20, background: C.light, borderRadius: 10, padding: "14px 16px" }}>
              <p style={{ margin: "0 0 8px", fontSize: 12, fontWeight: 600, color: C.text }}>핵심 인사이트</p>
              {[
                "Dense 단독으로도 Hit@1 64.9% 달성 — RAG 도입 효과 즉각적",
                "Hybrid 전환 시 Hit@1 +24.4pp 추가 개선 (BM25 형태소 분석 기여)",
                "Answer Correctness는 Dense → Hybrid 간 소폭 상승 (+0.09)",
                "Hit@3/5는 96% 이상 — 재검색 전략으로 커버리지 완성 가능",
              ].map((text, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "flex-start" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: C.amber, flexShrink: 0, marginTop: 4 }} />
                  <p style={{ margin: 0, fontSize: 11, color: C.muted, lineHeight: 1.5 }}>{text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Footer ── */}
      <div style={{ marginTop: 28, textAlign: "center", fontSize: 11, color: C.border }}>
        Gemini LLM-as-Judge · E5-small-ko Embedding · Kiwi BM25 · Alpha Blending α=0.7
      </div>
    </div>
  );
}
