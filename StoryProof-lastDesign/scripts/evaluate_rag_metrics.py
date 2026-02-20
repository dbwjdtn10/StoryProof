"""
RAG 지표 평가 스크립트 (LLM-as-a-Judge)
=========================================
ChatbotService의 RAG 파이프라인을 실행하고, Gemini가 4가지 지표로 채점합니다.

지표:
1. Context Relevance (컨텍스트 관련성) — 검색 결과가 질문에 관련 있는가
2. Faithfulness (충실도) — 답변이 컨텍스트에만 근거하는가 (환각 없는가)
3. Answer Relevance (답변 관련성) — 답변이 질문에 적절히 대답하는가
4. Answer Correctness (답변 정확도) — 답변이 정답과 의미적으로 일치하는가

사용법:
    python scripts/evaluate_rag_metrics.py --dataset eval_dataset.json
    python scripts/evaluate_rag_metrics.py --dataset eval_dataset.json --max-samples 5
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, List, Optional
from tqdm import tqdm
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from dotenv import load_dotenv
from backend.core.config import settings

load_dotenv()

# ===== 설정 =====
OUTPUT_FILE = "rag_eval_results.json"


# ===== LLM-as-a-Judge 프롬프트 =====
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
표현 방식이 달라도 핵심 의미가 같으면 높은 점수를 부여합니다.

평가 기준:
- 1점: 완전히 다른 내용
- 2점: 약간의 관련성만 있고 핵심이 다름
- 3점: 부분적으로 맞지만 중요한 부분 누락 또는 오류
- 4점: 핵심 의미는 일치하나 세부 차이 존재
- 5점: 정답과 완전히 일치 (표현 차이는 무관)

JSON으로 응답하세요:
{{"score": 1-5, "reason": "판정 사유"}}"""


def get_gemini_client():
    """Gemini API 클라이언트"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
    return genai.Client(api_key=api_key)


def judge_metric(client, prompt: str, max_retries: int = 3) -> Dict:
    """
    Gemini를 사용하여 단일 지표 채점
    
    Returns:
        {"score": int, "reason": str}
    """
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.1  # 일관된 채점을 위해 낮은 temperature
                }
            )
            result = json.loads(response.text)
            # 점수 유효성 검사
            score = int(result.get("score", 0))
            if 1 <= score <= 5:
                return {"score": score, "reason": result.get("reason", "")}
            else:
                print(f"  ⚠️ 유효하지 않은 점수 ({score}), 재시도...")
        except Exception as e:
            print(f"  ⚠️ 채점 실패 (시도 {attempt+1}/{max_retries}): {e}")
            time.sleep(1)
    
    return {"score": 0, "reason": "채점 실패"}


def resolve_novel_id(novel_filename: str) -> Optional[int]:
    """
    novel_filename(예: "KR_fantasy_alice.txt")으로 DB의 novel_id를 조회합니다.
    
    조회 전략 (순차 시도):
    1. Novel.title에 파일명 키워드 매칭 (alice → "앨리스", sherlock → "셜록" 등)
    2. Novel.title에 파일명 전체 포함 여부
    3. Chapter.title에 파일명 키워드 매칭
    """
    from backend.db.session import SessionLocal
    from backend.db.models import Novel, Chapter
    
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
        
        # 파일명에서 키워드 추출: "KR_fantasy_alice" → ["fantasy", "alice"]
        parts = clean_name.split('_')
        keywords = [p.lower() for p in parts if len(p) > 2 and p != "KR"]
        
        # 전략 1: 영문 키워드 → 한국어 변환 후 Novel.title 매칭
        for keyword in keywords:
            kr_keyword = FILENAME_KR_MAP.get(keyword)
            if kr_keyword:
                novel = db.query(Novel).filter(
                    Novel.title.ilike(f"%{kr_keyword}%")
                ).first()
                if novel:
                    print(f"  [Novel ID] 전략 1 성공: '{keyword}'→'{kr_keyword}' → title='{novel.title}' → novel_id={novel.id}")
                    return novel.id
        
        # 전략 2: 영문 키워드 그대로 Novel.title 검색 (영문 제목일 경우)
        for keyword in keywords:
            novel = db.query(Novel).filter(
                Novel.title.ilike(f"%{keyword}%")
            ).first()
            if novel:
                print(f"  [Novel ID] 전략 2 성공: 키워드 '{keyword}' → title='{novel.title}' → novel_id={novel.id}")
                return novel.id
        
        # 전략 3: Novel.title에 파일명 전체 포함 검색
        novel = db.query(Novel).filter(
            Novel.title.contains(clean_name)
        ).first()
        if novel:
            print(f"  [Novel ID] 전략 3 성공: 직접 매칭 → novel_id={novel.id}")
            return novel.id
        
        # 실패: 디버깅 정보 출력
        all_novels = db.query(Novel).all()
        print(f"  ⚠️ [Novel ID] 매칭 실패! '{novel_filename}'에 대응하는 소설을 찾을 수 없습니다.")
        print(f"  📋 DB에 등록된 소설 목록:")
        for n in all_novels[:10]:
            print(f"     - id={n.id}, title='{n.title}'")
        
        return None
        
    finally:
        db.close()


def run_rag_pipeline(question: str, novel_filename: str) -> Dict:
    """
    ChatbotService의 RAG 파이프라인 실행
    
    Returns:
        {"answer": str, "context": str, "chunks": list, "found_context": bool}
    """
    from backend.services.chatbot_service import ChatbotService
    
    service = ChatbotService()
    
    # novel_filename으로 novel_id 조회 (강화된 매칭)
    novel_id = resolve_novel_id(novel_filename)
    
    if novel_id is None:
        print(f"  ⚠️ novel_id를 찾지 못했습니다. novel_filter로 폴백합니다.")
    else:
        print(f"  ✅ novel_id={novel_id} 확인됨")
    
    # 하이브리드 검색 실행
    top_chunks = service.hybrid_search(
        question=question,
        novel_id=novel_id,
        # novel_id가 None이면 novel_filter로 Pinecone 메타데이터 필터링 시도
        novel_filter=novel_filename if novel_id is None else None
    )
    
    if not top_chunks:
        # 폴백: 원본 쿼리로 직접 검색
        top_chunks = service.find_similar_chunks(
            question=question,
            novel_id=novel_id,
            top_k=5,
            novel_filter=novel_filename if novel_id is None else None
        )
    
    if not top_chunks:
        return {
            "answer": "관련 내용을 찾을 수 없습니다.",
            "context": "",
            "chunks": [],
            "found_context": False
        }
    
    # 컨텍스트 조합
    context_texts = []
    for i, chunk in enumerate(top_chunks):
        header = f"[Context {i+1}]"
        if chunk.get('scene_index') is not None:
            header += f" Scene {chunk['scene_index']}"
        if chunk.get('summary'):
            header += f" ({chunk['summary']})"
        context_texts.append(f"{header}\n{chunk['text']}")
    
    context = "\n\n".join(context_texts)
    
    # 답변 생성
    answer = service.generate_answer(question, context)
    
    return {
        "answer": answer,
        "context": context,
        "chunks": [{"text": c.get("text", ""), "similarity": c.get("similarity", 0)} for c in top_chunks],
        "found_context": True,
        "novel_id_resolved": novel_id
    }


def evaluate_single_qa(client, qa: Dict, rag_result: Dict) -> Dict:
    """단일 QA 쌍에 대해 4가지 지표 모두 평가"""
    question = qa["question"]
    ground_truth = qa["answer"]
    context = rag_result["context"]
    answer = rag_result["answer"]
    
    metrics = {}
    
    # 1. Context Relevance
    prompt = CONTEXT_RELEVANCE_PROMPT.format(question=question, context=context)
    metrics["context_relevance"] = judge_metric(client, prompt)
    
    # 2. Faithfulness
    prompt = FAITHFULNESS_PROMPT.format(question=question, context=context, answer=answer)
    metrics["faithfulness"] = judge_metric(client, prompt)
    
    # 3. Answer Relevance
    prompt = ANSWER_RELEVANCE_PROMPT.format(question=question, answer=answer)
    metrics["answer_relevance"] = judge_metric(client, prompt)
    
    # 4. Answer Correctness
    prompt = ANSWER_CORRECTNESS_PROMPT.format(
        question=question, ground_truth=ground_truth, answer=answer
    )
    metrics["answer_correctness"] = judge_metric(client, prompt)
    
    return metrics


def compute_summary(results: List[Dict]) -> Dict:
    """전체 결과에서 요약 통계 계산"""
    metric_names = ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]
    summary = {}
    
    for metric in metric_names:
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
    
    # 카테고리별 통계
    category_stats = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in category_stats:
            category_stats[cat] = {m: [] for m in metric_names}
        for m in metric_names:
            score = r["metrics"][m]["score"]
            if score > 0:
                category_stats[cat][m].append(score)
    
    for cat, scores_dict in category_stats.items():
        for m in metric_names:
            scores = scores_dict[m]
            category_stats[cat][m] = round(sum(scores) / len(scores), 2) if scores else 0
    
    summary["by_category"] = category_stats
    
    # 소설별 통계
    novel_stats = {}
    for r in results:
        novel = r.get("novel_filename", "unknown")
        if novel not in novel_stats:
            novel_stats[novel] = {m: [] for m in metric_names}
        for m in metric_names:
            score = r["metrics"][m]["score"]
            if score > 0:
                novel_stats[novel][m].append(score)
    
    for novel, scores_dict in novel_stats.items():
        for m in metric_names:
            scores = scores_dict[m]
            novel_stats[novel][m] = round(sum(scores) / len(scores), 2) if scores else 0
    
    summary["by_novel"] = novel_stats
    
    return summary


def main():
    parser = argparse.ArgumentParser(description="RAG 지표 평가 (LLM-as-a-Judge)")
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
    
    rag_eval = dataset.get("rag_eval", [])
    if args.max_samples:
        rag_eval = rag_eval[:args.max_samples]
    
    print(f"📊 RAG 지표 평가 (LLM-as-a-Judge)")
    print(f"   데이터셋: {args.dataset}")
    print(f"   평가 샘플: {len(rag_eval)}개")
    print(f"   출력: {args.output}")
    print()
    
    client = get_gemini_client()
    results = []
    
    for i, qa in enumerate(tqdm(rag_eval, desc="RAG 평가 중")):
        print(f"\n[{i+1}/{len(rag_eval)}] Q: {qa['question'][:60]}...")
        
        # 1. RAG 파이프라인 실행
        rag_result = run_rag_pipeline(qa["question"], qa.get("novel_filename", ""))
        
        if not rag_result["found_context"]:
            print(f"  ⚠️ 컨텍스트를 찾지 못했습니다.")
            result_entry = {
                "question": qa["question"],
                "ground_truth": qa["answer"],
                "novel_filename": qa.get("novel_filename", ""),
                "category": qa.get("category", "unknown"),
                "rag_answer": rag_result["answer"],
                "context_found": False,
                "metrics": {
                    "context_relevance": {"score": 0, "reason": "컨텍스트 없음"},
                    "faithfulness": {"score": 0, "reason": "컨텍스트 없음"},
                    "answer_relevance": {"score": 0, "reason": "컨텍스트 없음"},
                    "answer_correctness": {"score": 0, "reason": "컨텍스트 없음"},
                }
            }
        else:
            # 2. LLM-as-a-Judge 채점
            metrics = evaluate_single_qa(client, qa, rag_result)
            
            result_entry = {
                "question": qa["question"],
                "ground_truth": qa["answer"],
                "novel_filename": qa.get("novel_filename", ""),
                "category": qa.get("category", "unknown"),
                "rag_answer": rag_result["answer"],
                "context_found": True,
                "context_preview": rag_result["context"][:500],
                "num_chunks": len(rag_result["chunks"]),
                "top_similarity": rag_result["chunks"][0]["similarity"] if rag_result["chunks"] else 0,
                "metrics": metrics
            }
            
            # 진행 상황 출력
            scores = {k: v["score"] for k, v in metrics.items()}
            print(f"  → 점수: {scores}")
        
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
    print(f"📊 RAG 평가 결과 요약")
    print(f"{'='*60}")
    for metric_name in ["context_relevance", "faithfulness", "answer_relevance", "answer_correctness"]:
        stats = summary.get(metric_name, {})
        mean = stats.get("mean", 0)
        bar = "█" * int(mean) + "░" * (5 - int(mean))
        print(f"  {metric_name:25s}: {bar} {mean}/5.0")
    
    print(f"\n✅ 상세 결과 저장: {args.output}")


if __name__ == "__main__":
    main()
