"""
Agent 지표 평가 스크립트 (LLM-as-a-Judge)
==========================================
StoryConsistencyAgent의 설정 일관성 검사를 실행하고, Gemini가 3가지 지표로 채점합니다.

지표:
1. Tool Use Accuracy (도구 활용 정확도) — 관련 컨텍스트를 올바르게 검색했는가
2. Reasoning Quality (추론 품질) — 판단 로직이 합리적인가
3. Output Completeness (출력 완전성) — 응답이 완전한가 (구절, 설명, 제안 포함)
+ 정확도(Accuracy) — expected_status와 실제 status 일치 여부

사용법:
    python scripts/evaluate_agent_metrics.py --dataset eval_dataset.json
    python scripts/evaluate_agent_metrics.py --dataset eval_dataset.json --max-samples 5
"""

import os
import sys
import json
import time
import asyncio
import argparse
from typing import Dict, List
from tqdm import tqdm
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from dotenv import load_dotenv
from backend.core.config import settings

load_dotenv()

# ===== 설정 =====
OUTPUT_FILE = "agent_eval_results.json"


# ===== LLM-as-a-Judge 프롬프트 =====
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
설정 충돌/일치 여부를 올바르게 판단했는지, 근거가 타당한지 평가합니다.

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

완전한 응답의 조건 (설정 파괴 감지 시):
- status 필드 존재
- 문제 구절(quote) 인용
- 문제 설명(description)
- 수정 제안(suggestion)
- results 배열에 세부 항목 포함

완전한 응답의 조건 (설정 일치 시):
- status 필드 존재
- 일치를 확인하는 간단한 설명

평가 기준:
- 1점: 필수 필드 대부분 누락, 불완전한 JSON
- 2점: 일부 필드만 존재, 핵심 정보 누락
- 3점: 기본 구조는 있으나 세부 사항 부족
- 4점: 대부분의 필드 존재, 약간의 보완 필요
- 5점: 모든 필수 필드가 완벽히 포함된 응답

JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""


def get_gemini_client():
    """Gemini API 클라이언트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
    return genai.Client(api_key=api_key)


def judge_metric(client, prompt: str, max_retries: int = 3) -> Dict:
    """Gemini를 사용하여 단일 지표 채점"""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.1
                }
            )
            result = json.loads(response.text)
            score = int(result.get("score", 0))
            if 1 <= score <= 5:
                return {"score": score, "reason": result.get("reason", "")}
        except Exception as e:
            print(f"  ⚠️ 채점 실패 (시도 {attempt+1}/{max_retries}): {e}")
            time.sleep(1)
    
    return {"score": 0, "reason": "채점 실패"}


def resolve_novel_id(novel_filename: str):
    """
    novel_filename(예: "KR_fantasy_alice.txt")으로 DB의 novel_id를 조회합니다.
    
    조회 전략 (순차 시도):
    1. 영문 키워드 → 한국어 변환 후 Novel.title 매칭
    2. 영문 키워드 그대로 Novel.title 검색
    3. Novel.title에 파일명 전체 포함 검색
    """
    from backend.db.session import SessionLocal
    from backend.db.models import Novel
    
    # 파일명에서 추출 가능한 영문 키워드 → 한국어 매핑
    FILENAME_KR_MAP = {
        "alice": "앨리스",
        "jane": "제인",
        "sherlock": "셜록",
        "frankenstein": "프랑켄",
        "jekyll": "지킬",
        "gatsby": "개츠비",
        "pride": "오만",
        "dracula": "드라큘라",
        "oz": "오즈",
        "peterpan": "피터팬",
        "treasure": "보물",
        "tomsawyer": "톰",
        "mobydick": "모비딕",
        "timemachine": "타임머신",
        "warofworlds": "우주전쟁",
        "karamazov": "카라마조프",
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
                novel = db.query(Novel).filter(
                    Novel.title.ilike(f"%{kr_keyword}%")
                ).first()
                if novel:
                    print(f"  [Novel ID] '{keyword}'→'{kr_keyword}' → title='{novel.title}' → id={novel.id}")
                    return novel.id
        
        # 전략 2: 영문 키워드 그대로 검색
        for keyword in keywords:
            novel = db.query(Novel).filter(
                Novel.title.ilike(f"%{keyword}%")
            ).first()
            if novel:
                print(f"  [Novel ID] 키워드 '{keyword}' → title='{novel.title}' → id={novel.id}")
                return novel.id
        
        # 전략 3: 파일명 전체 포함 검색
        novel = db.query(Novel).filter(Novel.title.contains(clean_name)).first()
        if novel:
            print(f"  [Novel ID] 직접 매칭 → id={novel.id}")
            return novel.id
        
        # 실패
        all_novels = db.query(Novel).all()
        print(f"  ⚠️ [Novel ID] '{novel_filename}' 매칭 실패!")
        print(f"  📋 DB 소설 목록:")
        for n in all_novels[:10]:
            print(f"     - id={n.id}, title='{n.title}'")
        return None
        
    finally:
        db.close()


def run_agent_check(input_text: str, novel_filename: str) -> Dict:
    """
    StoryConsistencyAgent 실행 (동기 래퍼)
    
    Returns:
        {"status": str, "results": list, "context_used": str, "raw_response": dict}
    """
    from backend.services.analysis.agent import StoryConsistencyAgent
    
    api_key = os.getenv("GOOGLE_API_KEY")
    agent = StoryConsistencyAgent(api_key=api_key)
    
    # novel_filename으로 novel_id 조회 (강화된 매칭)
    novel_id = resolve_novel_id(novel_filename)
    
    if not novel_id:
        return {
            "status": "오류",
            "results": [],
            "context_used": "",
            "raw_response": {"error": f"소설 '{novel_filename}'을 DB에서 찾을 수 없습니다."}
        }
    
    print(f"  ✅ novel_id={novel_id} 확인됨")
    
    # Agent의 check_consistency는 async이므로 asyncio.run으로 실행
    try:
        result = asyncio.run(agent.check_consistency(novel_id, input_text))
    except RuntimeError:
        # 이미 이벤트 루프가 실행 중인 경우
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.check_consistency(novel_id, input_text))
        finally:
            loop.close()
    
    # 검색된 컨텍스트 수집 (Agent 내부에서 사용한 것)
    search_results = agent.search_engine.search(
        input_text, novel_id=novel_id, top_k=5
    )
    context_texts = []
    for hit in search_results:
        doc = hit.get('document', {})
        text = doc.get('original_text', doc.get('text', ''))
        context_texts.append(text[:300])
    context_str = "\n---\n".join(context_texts)
    
    return {
        "status": result.get("status", "알 수 없음"),
        "results": result.get("results", []),
        "context_used": context_str,
        "raw_response": result,
        "novel_id_resolved": novel_id
    }


def evaluate_single_scenario(client, scenario: Dict, agent_result: Dict) -> Dict:
    """단일 시나리오에 대해 3가지 지표 + 정확도 평가"""
    input_text = scenario["input_text"]
    expected_status = scenario["expected_status"]
    scenario_type = scenario["scenario_type"]
    explanation = scenario.get("explanation", "설명 없음")
    
    agent_response_str = json.dumps(agent_result["raw_response"], ensure_ascii=False, indent=2)
    
    metrics = {}
    
    # 1. Tool Use Accuracy
    prompt = TOOL_USE_ACCURACY_PROMPT.format(
        input_text=input_text,
        retrieved_context=agent_result["context_used"][:2000],
        explanation=explanation
    )
    metrics["tool_use_accuracy"] = judge_metric(client, prompt)
    
    # 2. Reasoning Quality
    prompt = REASONING_QUALITY_PROMPT.format(
        input_text=input_text,
        expected_status=expected_status,
        scenario_type=scenario_type,
        explanation=explanation,
        agent_response=agent_response_str[:2000]
    )
    metrics["reasoning_quality"] = judge_metric(client, prompt)
    
    # 3. Output Completeness
    prompt = OUTPUT_COMPLETENESS_PROMPT.format(
        agent_response=agent_response_str[:2000],
        scenario_type=scenario_type
    )
    metrics["output_completeness"] = judge_metric(client, prompt)
    
    # 4. Accuracy (직접 비교)
    actual_status = agent_result["status"]
    # 부분 매칭: "설정 파괴" 또는 "설정 일치"가 포함되면 매칭
    status_match = False
    if "파괴" in expected_status and "파괴" in actual_status:
        status_match = True
    elif "일치" in expected_status and ("일치" in actual_status or "일관" in actual_status):
        status_match = True
    elif expected_status == actual_status:
        status_match = True
    
    metrics["accuracy"] = {
        "correct": status_match,
        "expected": expected_status,
        "actual": actual_status
    }
    
    return metrics


def compute_summary(results: List[Dict]) -> Dict:
    """결과 요약 통계 계산"""
    llm_metrics = ["tool_use_accuracy", "reasoning_quality", "output_completeness"]
    summary = {}
    
    # LLM 지표 통계
    for metric in llm_metrics:
        scores = [r["metrics"][metric]["score"] for r in results if r["metrics"][metric]["score"] > 0]
        if scores:
            summary[metric] = {
                "mean": round(sum(scores) / len(scores), 2),
                "min": min(scores),
                "max": max(scores),
                "count": len(scores)
            }
        else:
            summary[metric] = {"mean": 0, "min": 0, "max": 0, "count": 0}
    
    # 정확도 통계
    accuracy_results = [r["metrics"]["accuracy"] for r in results]
    correct_count = sum(1 for a in accuracy_results if a["correct"])
    total = len(accuracy_results)
    summary["accuracy"] = {
        "correct": correct_count,
        "total": total,
        "rate": round(correct_count / total, 4) if total > 0 else 0
    }
    
    # 시나리오 유형별 통계
    type_stats = {}
    for r in results:
        stype = r.get("scenario_type", "unknown")
        if stype not in type_stats:
            type_stats[stype] = {"correct": 0, "total": 0, "scores": {m: [] for m in llm_metrics}}
        type_stats[stype]["total"] += 1
        if r["metrics"]["accuracy"]["correct"]:
            type_stats[stype]["correct"] += 1
        for m in llm_metrics:
            score = r["metrics"][m]["score"]
            if score > 0:
                type_stats[stype]["scores"][m].append(score)
    
    for stype in type_stats:
        total = type_stats[stype]["total"]
        correct = type_stats[stype]["correct"]
        type_stats[stype]["accuracy_rate"] = round(correct / total, 4) if total > 0 else 0
        for m in llm_metrics:
            scores = type_stats[stype]["scores"][m]
            type_stats[stype][f"{m}_mean"] = round(sum(scores) / len(scores), 2) if scores else 0
        del type_stats[stype]["scores"]  # 원본 점수 리스트 제거
    
    summary["by_scenario_type"] = type_stats
    
    # 소설별 통계
    novel_stats = {}
    for r in results:
        novel = r.get("novel_filename", "unknown")
        if novel not in novel_stats:
            novel_stats[novel] = {"correct": 0, "total": 0}
        novel_stats[novel]["total"] += 1
        if r["metrics"]["accuracy"]["correct"]:
            novel_stats[novel]["correct"] += 1
    
    for novel in novel_stats:
        total = novel_stats[novel]["total"]
        correct = novel_stats[novel]["correct"]
        novel_stats[novel]["accuracy_rate"] = round(correct / total, 4) if total > 0 else 0
    
    summary["by_novel"] = novel_stats
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="Agent 지표 평가 (LLM-as-a-Judge)")
    parser.add_argument("--dataset", type=str, default="eval_dataset.json", help="평가 데이터셋 경로")
    parser.add_argument("--max-samples", type=int, default=None, help="최대 평가 샘플 수")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="결과 출력 경로")
    args = parser.parse_args()
    
    # 데이터셋 로드
    if not os.path.exists(args.dataset):
        print(f"❌ 데이터셋 파일 없음: {args.dataset}")
        print("   먼저 python scripts/generate_eval_dataset.py 를 실행하세요.")
        return
    
    with open(args.dataset, 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    agent_eval = dataset.get("agent_eval", [])
    if args.max_samples:
        agent_eval = agent_eval[:args.max_samples]
    
    print(f"🤖 Agent 지표 평가 (LLM-as-a-Judge)")
    print(f"   데이터셋: {args.dataset}")
    print(f"   평가 샘플: {len(agent_eval)}개")
    print(f"   출력: {args.output}")
    print()
    
    client = get_gemini_client()
    results = []
    
    for i, scenario in enumerate(tqdm(agent_eval, desc="Agent 평가 중")):
        input_text = scenario["input_text"]
        print(f"\n[{i+1}/{len(agent_eval)}] 시나리오: {input_text[:50]}...")
        print(f"  유형: {scenario['scenario_type']}, 예상: {scenario['expected_status']}")
        
        # 1. Agent 실행
        agent_result = run_agent_check(input_text, scenario.get("novel_filename", ""))
        print(f"  → Agent 판단: {agent_result['status']}")
        
        # 2. LLM-as-a-Judge 채점
        metrics = evaluate_single_scenario(client, scenario, agent_result)
        
        result_entry = {
            "input_text": input_text,
            "novel_filename": scenario.get("novel_filename", ""),
            "scenario_type": scenario["scenario_type"],
            "expected_status": scenario["expected_status"],
            "actual_status": agent_result["status"],
            "agent_results_count": len(agent_result["results"]),
            "context_preview": agent_result["context_used"][:300],
            "metrics": metrics
        }
        
        # 진행 상황 출력
        llm_scores = {k: v["score"] for k, v in metrics.items() if k != "accuracy"}
        print(f"  → LLM 점수: {llm_scores}")
        print(f"  → 정확도: {'✅' if metrics['accuracy']['correct'] else '❌'}")
        
        results.append(result_entry)
        
        # API 레이트 리밋 방지
        time.sleep(0.5)
    
    # 요약 통계 계산
    summary = compute_summary(results)
    
    # 최종 결과 저장
    output_data = {
        "metadata": {
            "evaluated_at": datetime.now().isoformat(),
            "total_samples": len(results),
            "dataset_source": args.dataset
        },
        "summary": summary,
        "details": results
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    # 결과 출력
    print(f"\n{'='*60}")
    print(f"🤖 Agent 평가 결과 요약")
    print(f"{'='*60}")
    
    for metric_name in ["tool_use_accuracy", "reasoning_quality", "output_completeness"]:
        stats = summary.get(metric_name, {})
        mean = stats.get("mean", 0)
        bar = "█" * int(mean) + "░" * (5 - int(mean))
        print(f"  {metric_name:25s}: {bar} {mean}/5.0")
    
    acc = summary.get("accuracy", {})
    acc_rate = acc.get("rate", 0) * 100
    print(f"  {'accuracy':25s}: {acc.get('correct', 0)}/{acc.get('total', 0)} ({acc_rate:.1f}%)")
    
    # 시나리오 유형별
    print(f"\n  📋 시나리오 유형별:")
    for stype, stats in summary.get("by_scenario_type", {}).items():
        print(f"    {stype}: 정확도 {stats['accuracy_rate']*100:.0f}%, "
              f"추론 {stats.get('reasoning_quality_mean', 0)}/5")
    
    print(f"\n✅ 상세 결과 저장: {args.output}")


if __name__ == "__main__":
    main()
