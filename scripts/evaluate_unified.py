"""
RAG & Agent 통합 평가 스크립트
==============================
생성된 데이터셋(eval_dataset.json)을 기반으로
16개 전체 소설에 대해 RAG 정확도와 Agent 일관성을 한 번에 평가합니다.

기능:
1. RAG 파이프라인 평가 (4개 지표)
2. Agent 일관성 검사 평가 (3개 지표 + 정확도)
3. 통합 결과 저장 (rag_eval_results.json, agent_eval_results.json)

사용법:
    python scripts/evaluate_unified.py
    python scripts/evaluate_unified.py --max-samples 10
"""

import os
import sys
import json
import time
import asyncio
import argparse
import numpy as np
from typing import Dict, List, Optional
from tqdm import tqdm
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from dotenv import load_dotenv
from backend.db.session import SessionLocal
from backend.db.models import Novel, Chapter
from backend.services.chatbot_service import ChatbotService
from backend.services.analysis.agent import StoryConsistencyAgent

load_dotenv()

# ===== 설정 =====
RAG_OUTPUT_FILE = "rag_eval_results.json"
AGENT_OUTPUT_FILE = "agent_eval_results.json"

# ===== 프롬프트 (RAG) =====
CONTEXT_RELEVANCE_PROMPT = """당신은 RAG 시스템의 검색 품질을 평가하는 전문가입니다.
[질문]: {question}
[검색된 컨텍스트]:
{context}
위 질문에 대해 검색된 컨텍스트가 얼마나 관련 있는지 1-5점으로 평가하세요.
평가 기준:
- 1점: 완전히 무관한 내용
- 2점: 약간의 관련성은 있지만 질문에 답하기 부족
- 3점: 부분적으로 관련 있으나 핵심 정보 부족
- 4점: 대부분 관련 있고 답변에 충분한 정보 포함
- 5점: 질문에 정확히 대응하는 높은 관련성
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""

FAITHFULNESS_PROMPT = """당신은 RAG 시스템의 답변 충실도를 평가하는 전문가입니다.
[질문]: {question}
[검색된 컨텍스트]:
{context}
[생성된 답변]:
{answer}
답변이 검색된 컨텍스트에만 근거하여 작성되었는지 1-5점으로 평가하세요.
컨텍스트에 없는 정보를 추가했다면(환각/hallucination) 감점합니다.
평가 기준:
- 1점: 답변의 대부분이 컨텍스트에 없는 정보 (심각한 환각)
- 2점: 많은 부분이 컨텍스트와 무관하거나 지어낸 내용
- 3점: 일부 환각이 있으나 핵심은 컨텍스트 기반
- 4점: 거의 모두 컨텍스트에 근거, 사소한 추론만 포함
- 5점: 완벽히 컨텍스트에만 근거한 답변
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""

ANSWER_RELEVANCE_PROMPT = """당신은 RAG 시스템의 답변 품질을 평가하는 전문가입니다.
[질문]: {question}
[생성된 답변]:
{answer}
답변이 질문에 얼마나 적절히 대답하는지 1-5점으로 평가하세요.
평가 기준:
- 1점: 질문과 전혀 관련 없는 답변
- 2점: 질문의 주제는 맞지만 핵심을 빗나감
- 3점: 부분적으로 답변하나 불완전
- 4점: 대체로 적절한 답변이나 약간의 보완 필요
- 5점: 질문에 정확하고 완벽하게 대답
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""

ANSWER_CORRECTNESS_PROMPT = """당신은 RAG 시스템의 답변 정확도를 평가하는 전문가입니다.
[질문]: {question}
[정답 (Ground Truth)]:
{ground_truth}
[생성된 답변]:
{answer}
생성된 답변이 정답과 의미적으로 얼마나 일치하는지 1-5점으로 평가하세요.
평가 기준:
- 1점: 완전히 다른 내용
- 2점: 약간의 관련성만 있고 핵심이 다름
- 3점: 부분적으로 맞지만 중요한 부분 누락 또는 오류
- 4점: 핵심 의미는 일치하나 세부 차이 존재
- 5점: 정답과 완전히 일치
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""

# ===== 프롬프트 (Agent) =====
TOOL_USE_ACCURACY_PROMPT = """당신은 AI Agent의 도구 활용 품질을 평가하는 전문가입니다.
[테스트 입력 문장]:
{input_text}
[Agent가 검색한 컨텍스트]:
{retrieved_context}
[시나리오 설명]:
{explanation}
Agent가 설정 일관성 검사를 위해 적절한 관련 컨텍스트를 검색했는지 1-5점으로 평가하세요.
평가 기준:
- 1점: 완전히 무관한 컨텍스트를 검색
- 2점: 약간 관련 있지만 판단에 부족
- 3점: 부분적으로 관련 있는 컨텍스트
- 4점: 대부분 관련 있고 판단에 충분한 정보
- 5점: 판단에 완벽히 적합한 높은 관련성의 컨텍스트
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""

REASONING_QUALITY_PROMPT = """당신은 AI Agent의 추론 품질을 평가하는 전문가입니다.
[테스트 입력 문장]:
{input_text}
[예상 결과]: {expected_status}
[시나리오 유형]: {scenario_type}
[시나리오 설명]: {explanation}
[Agent의 실제 응답]:
{agent_response}
Agent의 판단 로직이 합리적인지 1-5점으로 평가하세요.
평가 기준:
- 1점: 완전히 잘못된 판단, 논리적 오류
- 2점: 판단이 부정확하고 근거가 약함
- 3점: 부분적으로 맞는 판단이나 논리에 허점
- 4점: 대체로 합리적 판단, 사소한 개선 여지
- 5점: 완벽히 합리적이고 근거가 명확한 판단
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""

OUTPUT_COMPLETENESS_PROMPT = """당신은 AI Agent의 출력 품질을 평가하는 전문가입니다.
[Agent의 응답]:
{agent_response}
[시나리오 유형]: {scenario_type}
Agent의 응답이 완전한지 1-5점으로 평가하세요.
완전한 응답의 조건: status 필드, quote(파괴시), description, suggestion 등 포함 여부.
평가 기준:
- 1점: 필수 필드 대부분 누락
- 2점: 일부 필드만 존재
- 3점: 기본 구조는 있으나 세부 사항 부족
- 4점: 대부분의 필드 존재
- 5점: 모든 필수 필드가 완벽히 포함됨
JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""


def get_gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
    return genai.Client(api_key=api_key)


def judge_metric(client, prompt: str, max_retries: int = 3) -> Dict:
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={'response_mime_type': 'application/json', 'temperature': 0.1}
            )
            result = json.loads(response.text)
            score = int(result.get("score", 0))
            if 1 <= score <= 5:
                return {"score": score, "reason": result.get("reason", "")}
        except Exception as e:
            time.sleep(1)
    return {"score": 0, "reason": "채점 실패"}


def resolve_novel_id(novel_filename: str) -> Optional[int]:
    """파일명으로 novel_id 조회 (강화된 매칭 전략)"""
    FILENAME_KR_MAP = {
        "alice": "앨리스", "jane": "제인", "sherlock": "셜록",
        "frankenstein": "프랑켄", "jekyll": "지킬", "gatsby": "개츠비",
        "pride": "오만", "dracula": "드라큘라", "oz": "오즈",
        "peterpan": "피터팬", "treasure": "보물", "tomsawyer": "톰",
        "mobydick": "모비딕", "timemachine": "타임머신",
        "warofworlds": "우주전쟁", "karamazov": "카라마조프",
    }
    
    db = SessionLocal()
    try:
        clean_name = novel_filename.replace('.txt', '')
        parts = clean_name.split('_')
        keywords = [p.lower() for p in parts if len(p) > 2 and p != "KR"]
        
        # 전략 1: 영문 → 한국어 키워드 매칭
        for keyword in keywords:
            kr_keyword = FILENAME_KR_MAP.get(keyword)
            if kr_keyword:
                novel = db.query(Novel).filter(Novel.title.ilike(f"%{kr_keyword}%")).first()
                if novel: return novel.id
        
        # 전략 2: 영문 키워드 그대로 매칭
        for keyword in keywords:
            novel = db.query(Novel).filter(Novel.title.ilike(f"%{keyword}%")).first()
            if novel: return novel.id
            
        # 전략 3: 포함 검색
        novel = db.query(Novel).filter(Novel.title.contains(clean_name)).first()
        if novel: return novel.id
        
        return None
    finally:
        db.close()


# ===== RAG Logic =====
def run_rag_pipeline(question: str, novel_filename: str) -> Dict:
    service = ChatbotService()
    novel_id = resolve_novel_id(novel_filename)
    
    top_chunks = service.hybrid_search(
        question=question,
        novel_id=novel_id,
        novel_filter=novel_filename if novel_id is None else None
    )
    
    if not top_chunks:
        top_chunks = service.find_similar_chunks(
            question=question, novel_id=novel_id, top_k=5,
            novel_filter=novel_filename if novel_id is None else None
        )
    
    if not top_chunks:
        return {"answer": "내용 없음", "context": "", "chunks": [], "found_context": False}
    
    context_texts = [f"[Context {i+1}] {c['text']}" for i, c in enumerate(top_chunks)]
    context = "\n\n".join(context_texts)
    answer = service.generate_answer(question, context)
    
    return {
        "answer": answer, "context": context,
        "chunks": top_chunks, "found_context": True, "novel_id_resolved": novel_id
    }


def evaluate_rag(client, dataset: List[Dict]) -> List[Dict]:
    results = []
    print(f"\n📊 RAG 평가 시작 ({len(dataset)}개)")
    for qa in tqdm(dataset):
        rag_result = run_rag_pipeline(qa["question"], qa.get("novel_filename", ""))
        
        entry = {
            "question": qa["question"],
            "ground_truth": qa["answer"],
            "novel_filename": qa.get("novel_filename", ""),
            "category": qa.get("category", "unknown"),
            "rag_answer": rag_result["answer"],
            "metrics": {}
        }
        
        if rag_result["found_context"]:
            entry["context_found"] = True
            entry["context_preview"] = rag_result["context"][:300]
            
            # Metric Evaluation
            m = {}
            m["context_relevance"] = judge_metric(client, CONTEXT_RELEVANCE_PROMPT.format(
                question=qa["question"], context=rag_result["context"]))
            m["faithfulness"] = judge_metric(client, FAITHFULNESS_PROMPT.format(
                question=qa["question"], context=rag_result["context"], answer=rag_result["answer"]))
            m["answer_relevance"] = judge_metric(client, ANSWER_RELEVANCE_PROMPT.format(
                question=qa["question"], answer=rag_result["answer"]))
            m["answer_correctness"] = judge_metric(client, ANSWER_CORRECTNESS_PROMPT.format(
                question=qa["question"], ground_truth=qa["answer"], answer=rag_result["answer"]))
            entry["metrics"] = m
        else:
            entry["context_found"] = False
            zero = {"score": 0, "reason": "No context"}
            entry["metrics"] = {k: zero for k in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]}
            
        results.append(entry)
        time.sleep(0.5)
    return results


# ===== Agent Logic =====
def run_agent_check(input_text: str, novel_filename: str) -> Dict:
    api_key = os.getenv("GOOGLE_API_KEY")
    agent = StoryConsistencyAgent(api_key=api_key)
    novel_id = resolve_novel_id(novel_filename)
    
    if not novel_id:
        return {"status": "오류", "results": [], "context_used": "", "raw_response": {"error": "Novel not found"}}
    
    try:
        result = asyncio.run(agent.check_consistency(novel_id, input_text))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(agent.check_consistency(novel_id, input_text))
        loop.close()
        
    search_results = agent.search_engine.search(input_text, novel_id=novel_id, top_k=5)
    context_str = "\n---\n".join([hit['document'].get('original_text', '')[:300] for hit in search_results])
    
    return {
        "status": result.get("status", "알 수 없음"),
        "results": result.get("results", []),
        "context_used": context_str,
        "raw_response": result
    }


def evaluate_agent(client, dataset: List[Dict]) -> List[Dict]:
    results = []
    print(f"\n🤖 Agent 평가 시작 ({len(dataset)}개)")
    for scenario in tqdm(dataset):
        agent_result = run_agent_check(scenario["input_text"], scenario.get("novel_filename", ""))
        
        agent_resp_str = json.dumps(agent_result["raw_response"], ensure_ascii=False)
        m = {}
        
        # LLM Metrics
        m["tool_use_accuracy"] = judge_metric(client, TOOL_USE_ACCURACY_PROMPT.format(
            input_text=scenario["input_text"], retrieved_context=agent_result["context_used"][:2000],
            explanation=scenario.get("explanation", "")))
        
        m["reasoning_quality"] = judge_metric(client, REASONING_QUALITY_PROMPT.format(
            input_text=scenario["input_text"], expected_status=scenario["expected_status"],
            scenario_type=scenario["scenario_type"], explanation=scenario.get("explanation", ""),
            agent_response=agent_resp_str[:2000]))
            
        m["output_completeness"] = judge_metric(client, OUTPUT_COMPLETENESS_PROMPT.format(
            agent_response=agent_resp_str[:2000], scenario_type=scenario["scenario_type"]))
            
        # Accuracy
        ex_st = scenario["expected_status"]
        ac_st = agent_result["status"]
        correct = False
        if "파괴" in ex_st and "파괴" in ac_st: correct = True
        elif "일치" in ex_st and ("일치" in ac_st or "일관" in ac_st): correct = True
        elif ex_st == ac_st: correct = True
        
        m["accuracy"] = {"correct": correct, "expected": ex_st, "actual": ac_st}
        
        results.append({
            "input_text": scenario["input_text"],
            "novel_filename": scenario.get("novel_filename", ""),
            "scenario_type": scenario["scenario_type"],
            "metrics": m,
            "agent_results_count": len(agent_result["results"]),
            "expected_status": ex_st,
            "actual_status": ac_st
        })
        time.sleep(0.5)
    return results


def compute_rag_summary(results):
    summary = {}
    for m in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]:
        scores = [r["metrics"][m]["score"] for r in results if r["metrics"][m]["score"] > 0]
        summary[m] = {
            "mean": round(sum(scores)/len(scores), 2) if scores else 0,
            "count": len(scores)
        }
    
    # 카테고리별 통계
    by_category = {}
    for r in results:
        c = r.get("category", "unknown")
        if c not in by_category: by_category[c] = {k:[] for k in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]}
        for k in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]:
            s = r["metrics"][k]["score"]
            if s > 0: by_category[c][k].append(s)
            
    for c in by_category:
        for k in by_category[c]:
            vals = by_category[c][k]
            by_category[c][k] = round(sum(vals)/len(vals), 2) if vals else 0
    summary["by_category"] = by_category

    # 소설별 통계
    by_novel = {}
    for r in results:
        n = r["novel_filename"]
        if n not in by_novel: by_novel[n] = {k:[] for k in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]}
        for k in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]:
            s = r["metrics"][k]["score"]
            if s > 0: by_novel[n][k].append(s)
            
    for n in by_novel:
        for k in by_novel[n]:
            vals = by_novel[n][k]
            by_novel[n][k] = round(sum(vals)/len(vals), 2) if vals else 0
    summary["by_novel"] = by_novel
            
    return summary


def compute_agent_summary(results):
    summary = {}
    for m in ["tool_use_accuracy", "reasoning_quality", "output_completeness"]:
        scores = [r["metrics"][m]["score"] for r in results if r["metrics"][m]["score"] > 0]
        summary[m] = {"mean": round(sum(scores)/len(scores), 2) if scores else 0}
        
    correct = sum(1 for r in results if r["metrics"]["accuracy"]["correct"])
    summary["accuracy"] = {"rate": round(correct/len(results), 4) if results else 0, "correct": correct, "total": len(results)}
    
    # 시나리오 유형별 통계
    by_scenario_type = {}
    for r in results:
        t = r["scenario_type"]
        if t not in by_scenario_type: by_scenario_type[t] = {"correct": 0, "total": 0}
        by_scenario_type[t]["total"] += 1
        if r["metrics"]["accuracy"]["correct"]: by_scenario_type[t]["correct"] += 1
        
    for t in by_scenario_type:
        by_scenario_type[t]["accuracy_rate"] = round(by_scenario_type[t]["correct"]/by_scenario_type[t]["total"], 4)
        
    summary["by_scenario_type"] = by_scenario_type
    
    by_novel = {}
    for r in results:
        n = r["novel_filename"]
        if n not in by_novel: by_novel[n] = {"correct": 0, "total": 0}
        by_novel[n]["total"] += 1
        if r["metrics"]["accuracy"]["correct"]: by_novel[n]["correct"] += 1
        
    for n in by_novel:
        by_novel[n]["accuracy_rate"] = round(by_novel[n]["correct"]/by_novel[n]["total"], 4)
        
    summary["by_novel"] = by_novel
    return summary


def main():
    parser = argparse.ArgumentParser(description="RAG & Agent 통합 평가")
    parser.add_argument("--dataset", type=str, default="eval_dataset.json")
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()
    
    if not os.path.exists(args.dataset):
        print(f"❌ 데이터셋 '{args.dataset}'이 없습니다.")
        return
        
    with open(args.dataset, 'r', encoding='utf-8') as f:
        ds = json.load(f)
        
    client = get_gemini_client()
    
    # RAG Evaluation
    rag_data = ds.get("rag_eval", [])
    if args.max_samples: rag_data = rag_data[:args.max_samples]
    
    rag_results = evaluate_rag(client, rag_data)
    rag_summary = compute_rag_summary(rag_results)
    
    with open(RAG_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"metadata": {"total_samples": len(rag_results)}, "summary": rag_summary, "details": rag_results}, f, ensure_ascii=False, indent=2)
        
    # Agent Evaluation
    agent_data = ds.get("agent_eval", [])
    if args.max_samples: agent_data = agent_data[:args.max_samples]
    
    agent_results = evaluate_agent(client, agent_data)
    agent_summary = compute_agent_summary(agent_results)
    
    with open(AGENT_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({"metadata": {"total_samples": len(agent_results)}, "summary": agent_summary, "details": agent_results}, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ 통합 평가 완료!")
    print(f"   RAG 결과: {RAG_OUTPUT_FILE}")
    print(f"   Agent 결과: {AGENT_OUTPUT_FILE}")
    print(f"   이제 'python scripts/metrics_dashboard.py'를 실행하여 결과를 확인하세요.")

if __name__ == "__main__":
    main()
