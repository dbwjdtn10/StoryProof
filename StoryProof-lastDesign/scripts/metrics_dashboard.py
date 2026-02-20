"""
RAG & Agent 지표 시각화 대시보드
================================
평가 결과 JSON을 읽어 인터랙티브 HTML 대시보드를 생성합니다.

기능:
- RAG 4개 지표 레이더 차트
- Agent 3개 지표 + 정확도 바 차트
- 소설별/카테고리별 세부 분석 테이블
- 약점 항목 하이라이트

사용법:
    python scripts/metrics_dashboard.py
    python scripts/metrics_dashboard.py --rag-results rag_eval_results.json --agent-results agent_eval_results.json
"""

import os
import sys
import json
import argparse
from datetime import datetime

# ===== 설정 =====
RAG_RESULTS_FILE = "rag_eval_results.json"
AGENT_RESULTS_FILE = "agent_eval_results.json"
OUTPUT_HTML = "metrics_dashboard.html"


def load_json(filepath: str) -> dict:
    """JSON 파일 로드 (없으면 빈 딕셔너리 반환)"""
    if not os.path.exists(filepath):
        print(f"⚠️ 파일 없음: {filepath} (건너뜁니다)")
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_html(rag_data: dict, agent_data: dict) -> str:
    """결과 데이터를 기반으로 HTML 대시보드 생성"""
    
    # RAG 요약 데이터
    rag_summary = rag_data.get("summary", {})
    rag_metadata = rag_data.get("metadata", {})
    rag_details = rag_data.get("details", [])
    
    # Agent 요약 데이터
    agent_summary = agent_data.get("summary", {})
    agent_metadata = agent_data.get("metadata", {})
    agent_details = agent_data.get("details", [])
    
    # RAG 지표 점수
    rag_metrics = {
        "Context Relevance": rag_summary.get("context_relevance", {}).get("mean", 0),
        "Faithfulness": rag_summary.get("faithfulness", {}).get("mean", 0),
        "Answer Relevance": rag_summary.get("answer_relevance", {}).get("mean", 0),
        "Answer Correctness": rag_summary.get("answer_correctness", {}).get("mean", 0),
    }
    
    # Agent 지표 점수
    agent_metrics = {
        "Tool Use Accuracy": agent_summary.get("tool_use_accuracy", {}).get("mean", 0),
        "Reasoning Quality": agent_summary.get("reasoning_quality", {}).get("mean", 0),
        "Output Completeness": agent_summary.get("output_completeness", {}).get("mean", 0),
    }
    agent_accuracy = agent_summary.get("accuracy", {})
    
    # RAG 카테고리별 데이터
    rag_by_category = rag_summary.get("by_category", {})
    rag_by_novel = rag_summary.get("by_novel", {})
    
    # Agent 시나리오별 데이터
    agent_by_type = agent_summary.get("by_scenario_type", {})
    agent_by_novel = agent_summary.get("by_novel", {})
    
    # 약점 항목 (3점 이하)
    rag_weaknesses = []
    for detail in rag_details:
        for metric_key in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]:
            score = detail.get("metrics", {}).get(metric_key, {}).get("score", 0)
            if 0 < score <= 2:
                rag_weaknesses.append({
                    "question": detail.get("question", "")[:80],
                    "metric": metric_key,
                    "score": score,
                    "reason": detail.get("metrics", {}).get(metric_key, {}).get("reason", "")[:100]
                })
    
    agent_weaknesses = []
    for detail in agent_details:
        for metric_key in ["tool_use_accuracy", "reasoning_quality", "output_completeness"]:
            score = detail.get("metrics", {}).get(metric_key, {}).get("score", 0)
            if 0 < score <= 2:
                agent_weaknesses.append({
                    "input": detail.get("input_text", "")[:80],
                    "metric": metric_key,
                    "score": score,
                    "reason": detail.get("metrics", {}).get(metric_key, {}).get("reason", "")[:100]
                })
    
    # JSON 직렬화
    rag_metrics_json = json.dumps(rag_metrics, ensure_ascii=False)
    agent_metrics_json = json.dumps(agent_metrics, ensure_ascii=False)
    rag_by_category_json = json.dumps(rag_by_category, ensure_ascii=False)
    rag_by_novel_json = json.dumps(rag_by_novel, ensure_ascii=False)
    agent_by_type_json = json.dumps(agent_by_type, ensure_ascii=False)
    agent_by_novel_json = json.dumps(agent_by_novel, ensure_ascii=False)
    rag_weaknesses_json = json.dumps(rag_weaknesses[:10], ensure_ascii=False)
    agent_weaknesses_json = json.dumps(agent_weaknesses[:10], ensure_ascii=False)
    
    # 전체 평균 계산
    rag_values = [v for v in rag_metrics.values() if v > 0]
    rag_overall = round(sum(rag_values) / len(rag_values), 2) if rag_values else 0
    agent_values = [v for v in agent_metrics.values() if v > 0]
    agent_overall = round(sum(agent_values) / len(agent_values), 2) if agent_values else 0
    acc_rate = agent_accuracy.get("rate", 0) * 100
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StoryProof — RAG & Agent 평가 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0f1117;
            --bg-secondary: #1a1d28;
            --bg-card: #212636;
            --text-primary: #e8eaed;
            --text-secondary: #9aa0a6;
            --accent-blue: #4285f4;
            --accent-green: #34a853;
            --accent-yellow: #fbbc04;
            --accent-red: #ea4335;
            --accent-purple: #a855f7;
            --accent-cyan: #06b6d4;
            --border: #2e3345;
            --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-2: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            --gradient-3: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            --gradient-4: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px 24px;
        }}
        
        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        /* Overview Cards */
        .overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }}
        .stat-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
        }}
        .stat-card:nth-child(1)::before {{ background: var(--gradient-1); }}
        .stat-card:nth-child(2)::before {{ background: var(--gradient-2); }}
        .stat-card:nth-child(3)::before {{ background: var(--gradient-3); }}
        .stat-card:nth-child(4)::before {{ background: var(--gradient-4); }}
        .stat-card .label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        .stat-card .value {{
            font-size: 2.4rem;
            font-weight: 700;
        }}
        .stat-card .unit {{
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        
        /* Section */
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-title .icon {{
            font-size: 1.3rem;
        }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 36px;
        }}
        .chart-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
        }}
        .chart-card h3 {{
            font-size: 1.05rem;
            margin-bottom: 20px;
            color: var(--text-secondary);
        }}
        .chart-container {{
            position: relative;
            height: 320px;
        }}
        
        /* Tables */
        .table-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            overflow-x: auto;
        }}
        .table-card h3 {{
            font-size: 1.05rem;
            margin-bottom: 16px;
            color: var(--text-secondary);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        tr:hover td {{
            background: rgba(66, 133, 244, 0.05);
        }}
        
        /* Score Badge */
        .score-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
        }}
        .score-high {{ background: rgba(52, 168, 83, 0.2); color: #34a853; }}
        .score-mid {{ background: rgba(251, 188, 4, 0.2); color: #fbbc04; }}
        .score-low {{ background: rgba(234, 67, 53, 0.2); color: #ea4335; }}
        
        /* Weakness Alert */
        .weakness-item {{
            background: var(--bg-secondary);
            border-left: 3px solid var(--accent-red);
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 12px;
            font-size: 0.9rem;
        }}
        .weakness-item .wi-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
        }}
        .weakness-item .wi-metric {{
            color: var(--accent-yellow);
            font-weight: 600;
        }}
        .weakness-item .wi-reason {{
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        /* No Data */
        .no-data {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }}
        .no-data .emoji {{ font-size: 2rem; margin-bottom: 10px; }}
        
        /* Tabs */
        .tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 24px;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 4px;
            width: fit-content;
        }}
        .tab {{
            padding: 10px 24px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.9rem;
            color: var(--text-secondary);
            transition: all 0.2s;
            border: none;
            background: transparent;
        }}
        .tab.active {{
            background: var(--accent-blue);
            color: white;
        }}
        .tab:hover:not(.active) {{
            color: var(--text-primary);
        }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        @media (max-width: 768px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
            .overview {{ grid-template-columns: 1fr 1fr; }}
            .header h1 {{ font-size: 1.6rem; }}
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <!-- Header -->
        <div class="header">
            <h1>📊 StoryProof 평가 대시보드</h1>
            <p class="subtitle">RAG & Agent 성능 지표 — LLM-as-a-Judge 기반 자동 평가</p>
        </div>
        
        <!-- Overview Cards -->
        <div class="overview">
            <div class="stat-card">
                <div class="label">RAG 평균 점수</div>
                <div class="value" style="color: {_score_color(rag_overall)}">{rag_overall}</div>
                <div class="unit">/ 5.0</div>
            </div>
            <div class="stat-card">
                <div class="label">Agent 평균 점수</div>
                <div class="value" style="color: {_score_color(agent_overall)}">{agent_overall}</div>
                <div class="unit">/ 5.0</div>
            </div>
            <div class="stat-card">
                <div class="label">Agent 정확도</div>
                <div class="value" style="color: {_score_color(acc_rate / 20)}">{acc_rate:.0f}%</div>
                <div class="unit">{agent_accuracy.get('correct', 0)}/{agent_accuracy.get('total', 0)}</div>
            </div>
            <div class="stat-card">
                <div class="label">총 평가 수</div>
                <div class="value">{rag_metadata.get('total_samples', 0) + agent_metadata.get('total_samples', 0)}</div>
                <div class="unit">RAG {rag_metadata.get('total_samples', 0)} + Agent {agent_metadata.get('total_samples', 0)}</div>
            </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('rag')">📚 RAG 지표</button>
            <button class="tab" onclick="switchTab('agent')">🤖 Agent 지표</button>
            <button class="tab" onclick="switchTab('weakness')">⚠️ 약점 분석</button>
        </div>
        
        <!-- RAG Tab -->
        <div id="tab-rag" class="tab-content active">
            <div class="charts-grid">
                <div class="chart-card">
                    <h3>RAG 지표 레이더 차트</h3>
                    <div class="chart-container">
                        <canvas id="ragRadarChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>RAG 지표별 점수</h3>
                    <div class="chart-container">
                        <canvas id="ragBarChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="table-card" style="margin-bottom: 24px;">
                <h3>📖 소설별 RAG 성능</h3>
                <table>
                    <thead>
                        <tr>
                            <th>소설</th>
                            <th>Context Relevance</th>
                            <th>Faithfulness</th>
                            <th>Answer Relevance</th>
                            <th>Answer Correctness</th>
                        </tr>
                    </thead>
                    <tbody id="ragNovelTable"></tbody>
                </table>
            </div>
            
            <div class="table-card">
                <h3>🏷️ 카테고리별 RAG 성능</h3>
                <table>
                    <thead>
                        <tr>
                            <th>카테고리</th>
                            <th>Context Relevance</th>
                            <th>Faithfulness</th>
                            <th>Answer Relevance</th>
                            <th>Answer Correctness</th>
                        </tr>
                    </thead>
                    <tbody id="ragCategoryTable"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Agent Tab -->
        <div id="tab-agent" class="tab-content">
            <div class="charts-grid">
                <div class="chart-card">
                    <h3>Agent 지표 레이더 차트</h3>
                    <div class="chart-container">
                        <canvas id="agentRadarChart"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <h3>시나리오 유형별 정확도</h3>
                    <div class="chart-container">
                        <canvas id="agentAccChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="table-card">
                <h3>🤖 소설별 Agent 정확도</h3>
                <table>
                    <thead>
                        <tr><th>소설</th><th>정확</th><th>전체</th><th>정확도</th></tr>
                    </thead>
                    <tbody id="agentNovelTable"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Weakness Tab -->
        <div id="tab-weakness" class="tab-content">
            <div class="section">
                <h2 class="section-title"><span class="icon">📚</span> RAG 약점 (점수 ≤ 2)</h2>
                <div id="ragWeaknesses"></div>
            </div>
            <div class="section" style="margin-top: 32px;">
                <h2 class="section-title"><span class="icon">🤖</span> Agent 약점 (점수 ≤ 2)</h2>
                <div id="agentWeaknesses"></div>
            </div>
        </div>
    </div>
    
    <script>
    // === Data ===
    const ragMetrics = {rag_metrics_json};
    const agentMetrics = {agent_metrics_json};
    const ragByCategory = {rag_by_category_json};
    const ragByNovel = {rag_by_novel_json};
    const agentByType = {agent_by_type_json};
    const agentByNovel = {agent_by_novel_json};
    const ragWeaknesses = {rag_weaknesses_json};
    const agentWeaknesses = {agent_weaknesses_json};
    
    // === Utility ===
    function scoreBadge(score) {{
        if (score === 0) return '<span class="score-badge score-low">N/A</span>';
        const cls = score >= 4 ? 'score-high' : score >= 3 ? 'score-mid' : 'score-low';
        return `<span class="score-badge ${{cls}}">${{score.toFixed(1)}}</span>`;
    }}
    
    // === Tabs ===
    function switchTab(tabName) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById('tab-' + tabName).classList.add('active');
    }}
    
    // === RAG Charts ===
    const ragLabels = Object.keys(ragMetrics);
    const ragValues = Object.values(ragMetrics);
    
    if (ragValues.some(v => v > 0)) {{
        new Chart(document.getElementById('ragRadarChart'), {{
            type: 'radar',
            data: {{
                labels: ragLabels,
                datasets: [{{
                    label: 'RAG 점수',
                    data: ragValues,
                    backgroundColor: 'rgba(66, 133, 244, 0.2)',
                    borderColor: '#4285f4',
                    borderWidth: 2,
                    pointBackgroundColor: '#4285f4',
                    pointRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ r: {{ min: 0, max: 5, ticks: {{ stepSize: 1, color: '#9aa0a6' }}, grid: {{ color: '#2e3345' }}, pointLabels: {{ color: '#e8eaed', font: {{ size: 11 }} }} }} }},
                plugins: {{ legend: {{ labels: {{ color: '#e8eaed' }} }} }}
            }}
        }});
        
        new Chart(document.getElementById('ragBarChart'), {{
            type: 'bar',
            data: {{
                labels: ragLabels,
                datasets: [{{
                    label: '점수',
                    data: ragValues,
                    backgroundColor: ['rgba(102, 126, 234, 0.7)', 'rgba(79, 172, 254, 0.7)', 'rgba(67, 233, 123, 0.7)', 'rgba(250, 112, 154, 0.7)'],
                    borderColor: ['#667eea', '#4facfe', '#43e97b', '#fa709a'],
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ y: {{ min: 0, max: 5, ticks: {{ color: '#9aa0a6' }}, grid: {{ color: '#2e3345' }} }}, x: {{ ticks: {{ color: '#9aa0a6' }}, grid: {{ display: false }} }} }},
                plugins: {{ legend: {{ display: false }} }}
            }}
        }});
    }}
    
    // === Agent Charts ===
    const agentLabels = Object.keys(agentMetrics);
    const agentValues = Object.values(agentMetrics);
    
    if (agentValues.some(v => v > 0)) {{
        new Chart(document.getElementById('agentRadarChart'), {{
            type: 'radar',
            data: {{
                labels: agentLabels,
                datasets: [{{
                    label: 'Agent 점수',
                    data: agentValues,
                    backgroundColor: 'rgba(168, 85, 247, 0.2)',
                    borderColor: '#a855f7',
                    borderWidth: 2,
                    pointBackgroundColor: '#a855f7',
                    pointRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ r: {{ min: 0, max: 5, ticks: {{ stepSize: 1, color: '#9aa0a6' }}, grid: {{ color: '#2e3345' }}, pointLabels: {{ color: '#e8eaed', font: {{ size: 11 }} }} }} }},
                plugins: {{ legend: {{ labels: {{ color: '#e8eaed' }} }} }}
            }}
        }});
    }}
    
    // Agent Accuracy by Scenario Type
    const typeLabels = Object.keys(agentByType);
    const typeAccRates = typeLabels.map(t => (agentByType[t].accuracy_rate || 0) * 100);
    
    if (typeLabels.length > 0) {{
        new Chart(document.getElementById('agentAccChart'), {{
            type: 'bar',
            data: {{
                labels: typeLabels.map(l => l === 'consistent' ? '설정 일치 시나리오' : '설정 파괴 시나리오'),
                datasets: [{{
                    label: '정확도 (%)',
                    data: typeAccRates,
                    backgroundColor: ['rgba(52, 168, 83, 0.7)', 'rgba(234, 67, 53, 0.7)'],
                    borderColor: ['#34a853', '#ea4335'],
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ y: {{ min: 0, max: 100, ticks: {{ color: '#9aa0a6', callback: v => v + '%' }}, grid: {{ color: '#2e3345' }} }}, x: {{ ticks: {{ color: '#9aa0a6' }}, grid: {{ display: false }} }} }},
                plugins: {{ legend: {{ display: false }} }}
            }}
        }});
    }}
    
    // === Tables ===
    // RAG Novel Table
    const ragNovelTbody = document.getElementById('ragNovelTable');
    for (const [novel, scores] of Object.entries(ragByNovel)) {{
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${{novel.replace('.txt','')}}</td>
            <td>${{scoreBadge(scores.context_relevance || 0)}}</td>
            <td>${{scoreBadge(scores.faithfulness || 0)}}</td>
            <td>${{scoreBadge(scores.answer_relevance || 0)}}</td>
            <td>${{scoreBadge(scores.answer_correctness || 0)}}</td>
        `;
        ragNovelTbody.appendChild(row);
    }}
    if (Object.keys(ragByNovel).length === 0) {{
        ragNovelTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-secondary);">데이터 없음</td></tr>';
    }}
    
    // RAG Category Table
    const ragCatTbody = document.getElementById('ragCategoryTable');
    for (const [cat, scores] of Object.entries(ragByCategory)) {{
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${{cat}}</td>
            <td>${{scoreBadge(scores.context_relevance || 0)}}</td>
            <td>${{scoreBadge(scores.faithfulness || 0)}}</td>
            <td>${{scoreBadge(scores.answer_relevance || 0)}}</td>
            <td>${{scoreBadge(scores.answer_correctness || 0)}}</td>
        `;
        ragCatTbody.appendChild(row);
    }}
    if (Object.keys(ragByCategory).length === 0) {{
        ragCatTbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-secondary);">데이터 없음</td></tr>';
    }}
    
    // Agent Novel Table
    const agentNovelTbody = document.getElementById('agentNovelTable');
    for (const [novel, stats] of Object.entries(agentByNovel)) {{
        const row = document.createElement('tr');
        const rate = ((stats.accuracy_rate || 0) * 100).toFixed(0);
        const cls = rate >= 80 ? 'score-high' : rate >= 50 ? 'score-mid' : 'score-low';
        row.innerHTML = `
            <td>${{novel.replace('.txt','')}}</td>
            <td>${{stats.correct}}</td>
            <td>${{stats.total}}</td>
            <td><span class="score-badge ${{cls}}">${{rate}}%</span></td>
        `;
        agentNovelTbody.appendChild(row);
    }}
    if (Object.keys(agentByNovel).length === 0) {{
        agentNovelTbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text-secondary);">데이터 없음</td></tr>';
    }}
    
    // === Weaknesses ===
    function renderWeaknesses(containerId, items, typeLabel) {{
        const container = document.getElementById(containerId);
        if (items.length === 0) {{
            container.innerHTML = '<div class="no-data"><div class="emoji">✨</div>점수 2점 이하 항목이 없습니다!</div>';
            return;
        }}
        items.forEach(item => {{
            const div = document.createElement('div');
            div.className = 'weakness-item';
            const text = item.question || item.input || '';
            div.innerHTML = `
                <div class="wi-header">
                    <span>${{text}}</span>
                    <span class="wi-metric">${{item.metric}} = ${{item.score}}/5</span>
                </div>
                <div class="wi-reason">${{item.reason}}</div>
            `;
            container.appendChild(div);
        }});
    }}
    
    renderWeaknesses('ragWeaknesses', ragWeaknesses, 'RAG');
    renderWeaknesses('agentWeaknesses', agentWeaknesses, 'Agent');
    </script>
</body>
</html>"""
    
    return html


def _score_color(score: float) -> str:
    """점수에 따른 색상 반환"""
    if score >= 4:
        return "#34a853"
    elif score >= 3:
        return "#fbbc04"
    else:
        return "#ea4335"


def main():
    parser = argparse.ArgumentParser(description="RAG & Agent 평가 대시보드 생성")
    parser.add_argument("--rag-results", type=str, default=RAG_RESULTS_FILE, help="RAG 평가 결과 JSON")
    parser.add_argument("--agent-results", type=str, default=AGENT_RESULTS_FILE, help="Agent 평가 결과 JSON")
    parser.add_argument("--output", type=str, default=OUTPUT_HTML, help="출력 HTML 경로")
    args = parser.parse_args()
    
    print(f"📊 RAG & Agent 평가 대시보드 생성기")
    print(f"   RAG 결과: {args.rag_results}")
    print(f"   Agent 결과: {args.agent_results}")
    print(f"   출력: {args.output}")
    print()
    
    rag_data = load_json(args.rag_results)
    agent_data = load_json(args.agent_results)
    
    if not rag_data and not agent_data:
        print("❌ RAG 또는 Agent 평가 결과 파일이 필요합니다.")
        print("   먼저 evaluate_rag_metrics.py 또는 evaluate_agent_metrics.py를 실행하세요.")
        return
    
    html = generate_html(rag_data, agent_data)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 대시보드 생성 완료: {args.output}")
    print(f"   브라우저에서 열어 확인하세요!")


if __name__ == "__main__":
    main()
