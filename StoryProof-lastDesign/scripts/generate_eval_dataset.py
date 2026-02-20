"""
RAG & Agent 평가 데이터셋 생성기
================================
Gemini를 사용하여 소설 텍스트로부터 RAG QA 쌍 + Agent 일관성 시나리오를 자동 생성합니다.

사용법:
    python scripts/generate_eval_dataset.py                    # 기본 실행
    python scripts/generate_eval_dataset.py --dry-run          # API 호출 없이 구조 검증
    python scripts/generate_eval_dataset.py --novels 3         # 소설 3개만 사용
    python scripts/generate_eval_dataset.py --qa-per-novel 5   # 소설당 QA 5개
"""

import os
import sys
import json
import random
import argparse
from typing import List, Dict
from tqdm import tqdm

# 프로젝트 루트를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from dotenv import load_dotenv

load_dotenv()

# ===== 설정 =====
NOVEL_DIR = "novel_corpus_kr"
OUTPUT_FILE = "eval_dataset.json"

# 평가에 사용할 소설 목록 (다양한 장르 포함)
DEFAULT_NOVELS = [
    "KR_fantasy_alice.txt",
    "KR_romance_jane.txt",
    "KR_mystery_sherlock.txt",
    "KR_sf_frankenstein.txt",
    "KR_horror_jekyll.txt",
]


def get_gemini_client():
    """Gemini API 클라이언트 초기화"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return genai.Client(api_key=api_key)


def load_novel_text(filepath: str) -> str:
    """소설 텍스트 파일 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def extract_text_samples(text: str, num_samples: int = 3, sample_size: int = 5000) -> List[str]:
    """
    소설 텍스트에서 균등하게 분산된 샘플 추출
    앞부분, 중간, 뒷부분에서 각각 추출하여 다양한 내용 커버
    """
    text_len = len(text)
    if text_len < sample_size:
        return [text]
    
    samples = []
    positions = [0, text_len // 3, (text_len * 2) // 3]
    
    for pos in positions[:num_samples]:
        end = min(pos + sample_size, text_len)
        samples.append(text[pos:end])
    
    return samples


def generate_rag_qa_pairs(client, novel_title: str, text_chunk: str, num_pairs: int = 5) -> List[Dict]:
    """
    RAG 평가용 QA 쌍 생성
    
    카테고리:
    - factual: 사실 기반 질문 (누가, 어디서, 무엇을)
    - reasoning: 추론 필요 질문 (왜, 어떻게)
    - detail: 세부 묘사/대사 관련 질문
    """
    prompt = f"""다음 소설의 일부를 읽고, 이 내용에 대한 질문과 답변(QA) 쌍을 {num_pairs}개 생성하세요.

[소설 제목]: {novel_title}

[내용]:
{text_chunk[:8000]}

[요구사항]
1. 다양한 유형의 질문을 생성하세요:
   - "factual": 사실 기반 (누가, 어디서, 무엇을 했는지)
   - "reasoning": 추론/분석 (왜, 어떤 의미인지)
   - "detail": 세부 묘사 (대사, 외모, 감정 표현 등)
2. 답변은 본문에 근거하여 2-3문장으로 작성하세요.
3. source_segment에는 정답의 근거가 되는 본문 문장을 정확히 인용하세요.

[출력: JSON 배열]
[
    {{
        "question": "질문 내용",
        "answer": "답변 내용",
        "source_segment": "본문에서 인용한 근거 문장",
        "category": "factual|reasoning|detail"
    }}
]"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        results = json.loads(response.text)
        # 카테고리 유효성 검사
        valid_categories = {"factual", "reasoning", "detail"}
        for r in results:
            if r.get("category") not in valid_categories:
                r["category"] = "factual"
        return results
    except Exception as e:
        print(f"  ⚠️ RAG QA 생성 실패 ({novel_title}): {e}")
        return []


def generate_agent_scenarios(client, novel_title: str, text_chunk: str, num_pairs: int = 4) -> List[Dict]:
    """
    Agent 평가용 일관/비일관 시나리오 생성
    
    시나리오 유형:
    - consistent: 설정과 일치하는 문장
    - inconsistent: 설정과 모순되는 문장 (설정 파괴)
    """
    prompt = f"""다음 소설의 일부를 읽고, 설정 일관성 검사 테스트용 문장을 생성하세요.

[소설 제목]: {novel_title}

[내용]:
{text_chunk[:8000]}

[요구사항]
1. "consistent" {num_pairs // 2}개: 소설의 설정/세계관과 일치하는 문장
2. "inconsistent" {num_pairs // 2}개: 소설의 설정/세계관과 명백히 모순되는 문장
   - 캐릭터 성격 변경, 장소 설정 오류, 시대 모순 등을 포함
3. inconsistent에는 어떤 설정과 충돌하는지 explanation을 포함하세요.

[출력: JSON 배열]
[
    {{
        "input_text": "테스트할 문장 (2-3문장)",
        "expected_status": "설정 일치" 또는 "설정 파괴 감지",
        "scenario_type": "consistent" 또는 "inconsistent",
        "explanation": "일관/비일관의 이유 설명"
    }}
]"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        results = json.loads(response.text)
        # 유효성 검사
        for r in results:
            if r.get("scenario_type") not in {"consistent", "inconsistent"}:
                r["scenario_type"] = "consistent"
            if r.get("scenario_type") == "consistent":
                r["expected_status"] = "설정 일치"
            else:
                r["expected_status"] = "설정 파괴 감지"
        return results
    except Exception as e:
        print(f"  ⚠️ Agent 시나리오 생성 실패 ({novel_title}): {e}")
        return []


def generate_dry_run_data(novels: List[str]) -> Dict:
    """--dry-run 모드: API 호출 없이 더미 데이터 생성"""
    dataset = {"rag_eval": [], "agent_eval": []}
    
    for novel in novels:
        # RAG 더미 데이터
        dataset["rag_eval"].append({
            "question": f"[DRY-RUN] {novel}에 대한 테스트 질문",
            "answer": "[DRY-RUN] 테스트 답변",
            "source_segment": "[DRY-RUN] 테스트 근거 문장",
            "category": "factual",
            "novel_filename": novel
        })
        # Agent 더미 데이터
        dataset["agent_eval"].extend([
            {
                "input_text": f"[DRY-RUN] {novel} 일관 시나리오",
                "expected_status": "설정 일치",
                "scenario_type": "consistent",
                "explanation": "[DRY-RUN] 테스트 설명",
                "novel_filename": novel
            },
            {
                "input_text": f"[DRY-RUN] {novel} 비일관 시나리오",
                "expected_status": "설정 파괴 감지",
                "scenario_type": "inconsistent",
                "explanation": "[DRY-RUN] 테스트 설명",
                "novel_filename": novel
            }
        ])
    
    return dataset


def main():
    parser = argparse.ArgumentParser(description="RAG & Agent 평가 데이터셋 생성")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 구조만 검증")
    parser.add_argument("--novels", type=int, default=5, help="사용할 소설 수 (기본: 5)")
    parser.add_argument("--qa-per-novel", type=int, default=10, help="소설당 QA 쌍 수 (기본: 10)")
    parser.add_argument("--agent-per-novel", type=int, default=6, help="소설당 Agent 시나리오 수 (기본: 6)")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="출력 파일 경로")
    args = parser.parse_args()
    
    # 소설 목록 동적 스캔 (KR_*.txt)
    import glob
    novel_files = glob.glob(os.path.join(NOVEL_DIR, "KR_*.txt"))
    novels_to_use = [os.path.basename(f) for f in novel_files]
    
    # 앨리스2장 등 파편화된 파일 제외 (선택적)
    novels_to_use = [n for n in novels_to_use if "KR_" in n]
    novels_to_use.sort()
    
    if args.novels < len(novels_to_use):
        novels_to_use = novels_to_use[:args.novels]
    
    print(f"📊 RAG & Agent 평가 데이터셋 생성기")
    print(f"   소설: {len(novels_to_use)}개")
    print(f"   RAG QA/소설: {args.qa_per_novel}개")
    print(f"   Agent 시나리오/소설: {args.agent_per_novel}개")
    print(f"   출력: {args.output}")
    print()
    
    # Dry-run 모드
    if args.dry_run:
        print("🏃 DRY-RUN 모드: API 호출 없이 데이터 구조 검증")
        dataset = generate_dry_run_data(novels_to_use)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        print(f"✅ 더미 데이터 생성 완료: {args.output}")
        print(f"   RAG 평가: {len(dataset['rag_eval'])}개")
        print(f"   Agent 평가: {len(dataset['agent_eval'])}개")
        return
    
    # 실제 실행
    client = get_gemini_client()
    dataset = {"rag_eval": [], "agent_eval": []}
    
    for novel_filename in tqdm(novels_to_use, desc="소설 처리 중"):
        filepath = os.path.join(NOVEL_DIR, novel_filename)
        if not os.path.exists(filepath):
            print(f"⚠️ 파일 없음: {filepath}, 건너뜁니다.")
            continue
        
        print(f"\n📖 {novel_filename} 처리 중...")
        text = load_novel_text(filepath)
        samples = extract_text_samples(text, num_samples=3)
        
        # RAG QA 생성 (여러 샘플에서 분산 생성)
        qa_per_sample = max(1, args.qa_per_novel // len(samples))
        for i, sample in enumerate(samples):
            print(f"  [RAG] 샘플 {i+1}/{len(samples)} ({qa_per_sample}개 생성)...")
            qa_pairs = generate_rag_qa_pairs(client, novel_filename, sample, qa_per_sample)
            for qa in qa_pairs:
                qa['novel_filename'] = novel_filename
                dataset['rag_eval'].append(qa)
        
        # Agent 시나리오 생성
        print(f"  [Agent] 시나리오 {args.agent_per_novel}개 생성...")
        scenarios = generate_agent_scenarios(client, novel_filename, samples[0], args.agent_per_novel)
        for sc in scenarios:
            sc['novel_filename'] = novel_filename
            dataset['agent_eval'].append(sc)
    
    # 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 데이터셋 생성 완료: {args.output}")
    print(f"   RAG 평가: {len(dataset['rag_eval'])}개")
    print(f"   Agent 평가: {len(dataset['agent_eval'])}개")
    
    # 카테고리별 통계
    categories = {}
    for qa in dataset['rag_eval']:
        cat = qa.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    print(f"   RAG 카테고리 분포: {categories}")
    
    scenario_types = {}
    for sc in dataset['agent_eval']:
        st = sc.get('scenario_type', 'unknown')
        scenario_types[st] = scenario_types.get(st, 0) + 1
    print(f"   Agent 시나리오 분포: {scenario_types}")


if __name__ == "__main__":
    main()
