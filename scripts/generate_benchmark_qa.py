import os
import json
import random
import glob
from typing import List, Dict
from tqdm import tqdm
from google import genai
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 설정
NOVEL_DIR = "novel_corpus_kr"
OUTPUT_FILE = "benchmark_qa.json"
NUM_QA_PER_NOVEL = 10
SELECTED_NOVELS = [
    "KR_fantasy_alice.txt",
    "KR_romance_jane.txt",
    "KR_mystery_sherlock.txt"
]

def get_gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
    return genai.Client(api_key=api_key)

def load_novel_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def generate_qa_pairs(client, novel_title: str, text_chunk: str, num_pairs: int = 5) -> List[Dict]:
    prompt = f"""
    다음 소설의 일부를 읽고, 이 내용에 대한 질문과 답변(QA) 쌍을 {num_pairs}개 생성해주세요.
    
    [소설 제목]
    {novel_title}
    
    [내용]
    {text_chunk[:10000]} ... (생략)
    
    [요구사항]
    1. 질문은 소설의 구체적인 내용(사건, 인물, 대사, 장소 등)을 물어봐야 합니다.
    2. 답변은 본문에 근거하여 명확하게 작성해주세요.
    3. 'source_segment'에는 정답을 찾을 수 있는 본문의 핵심 문장이나 문단을 인용해주세요.
    4. JSON 형식으로만 응답해주세요.
    
    [출력 형식]
    [
        {{
            "question": "앨리스가 토끼를 따라 들어간 곳은?",
            "answer": "앨리스는 토끼를 따라 깊은 토끼굴로 떨어졌습니다.",
            "source_segment": "토끼굴은 처음에는 터널처럼 똑바로 뻗어 있더니 갑자기 푹 꺼져 버렸습니다."
        }},
        ...
    ]
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                'response_mime_type': 'application/json'
            }
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating QA for {novel_title}: {e}")
        return []

def main():
    client = get_gemini_client()
    all_qa_data = []
    
    print(f"Start generating QA benchmarks for {len(SELECTED_NOVELS)} novels...")
    
    for filename in SELECTED_NOVELS:
        filepath = os.path.join(NOVEL_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Warning: File not found {filepath}, skipping...")
            continue
            
        print(f"Processing {filename}...")
        text = load_novel_text(filepath)
        
        # 텍스트가 너무 길면 랜덤하게 앞부분이나 중간 부분을 샘플링
        # 여기서는 앞부분 20000자 정도만 사용해서 생성 (컨텍스트 윈도우 고려)
        sample_text = text[:20000] 
        
        qa_pairs = generate_qa_pairs(client, filename, sample_text, NUM_QA_PER_NOVEL)
        
        for qa in qa_pairs:
            qa['novel_filename'] = filename
            all_qa_data.append(qa)
            
        print(f"  - Generated {len(qa_pairs)} pairs")
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_qa_data, f, ensure_ascii=False, indent=2)
        
    print(f"Done! Saved {len(all_qa_data)} QA pairs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
