import os
import sys
import json
import random
import time
import torch
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings

# Configuration
CORPUS_FILE = "large_corpus.json"
OUTPUT_FILE = "large_benchmark_qa.json"
QA_PER_NOVEL = 100
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

def load_corpus(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_local_model():
    """Load Qwen 7B Key model with 4-bit quantization for 8GB VRAM"""
    print(f"Loading local model: {MODEL_ID} (4-bit)...")
    
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True
    )
    return model, tokenizer

def generate_qa_batch_local(model, tokenizer, chunks: list, novel_title: str) -> list:
    """Generates QA pair using local Qwen model"""
    
    # Select a random chunk that has enough content
    target_chunk = random.choice([c for c in chunks if len(c['text']) > 200])
    text_segment = target_chunk['text']
    
    system_prompt = "다음에 제공되는 소설 텍스트를 읽고, 질문과 답변을 생성하세요. 반드시 JSON 형식으로만 응답해야 합니다."
    user_prompt = f"""
    [소설 텍스트]
    {text_segment}
    
    위 텍스트에서 답을 찾을 수 있는 '사실 기반의 질문' 1개와 그에 대한 '답변'을 생성해주세요.
    
    조건:
    1. 질문은 텍스트 내의 정보만으로 답할 수 있어야 합니다.
    2. 답변은 핵심 키워드를 포함해야 합니다.
    3. 출력 형식은 오직 JSON이어야 합니다: {{ "question": "...", "answer": "..." }}
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    # Generate
    generated_ids = model.generate(
        model_inputs.input_ids,
        max_new_tokens=256,
        temperature=0.3,
        do_sample=True
    )
    
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    # Simple parsing check
    try:
        # Finding JSON part loosely
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = response_text[start:end]
            qa = json.loads(json_str)
            
            if "question" in qa and "answer" in qa:
                qa['novel_filename'] = novel_title
                qa['source_segment'] = text_segment
                return qa
    except Exception as e:
        # print(f"JSON Parse Error: {e} | Text: {response_text[:50]}...")
        pass
        
    return None

def main():
    load_dotenv()
    
    print(f"Loading corpus from {CORPUS_FILE}...")
    if not os.path.exists(CORPUS_FILE):
        print("Corpus file not found. Run prepare_large_benchmark.py first.")
        return
        
    corpus = load_corpus(CORPUS_FILE)
    
    # Group by Novel
    novel_chunks = {}
    for item in corpus:
        fname = item['novel_filename']
        if fname not in novel_chunks:
            novel_chunks[fname] = []
        novel_chunks[fname].append(item)
        
    print(f"Found {len(novel_chunks)} novels in corpus.")
    
    # Load Model (Once)
    model, tokenizer = load_local_model()
    
    all_qa_pairs = []
    
    # Generate
    for novel, chunks in tqdm(novel_chunks.items(), desc="Generating QA"):
        novel_qa_count = 0
        failures = 0
        
        pbar = tqdm(total=QA_PER_NOVEL, desc=f"  > {novel}", leave=False)
        
        while novel_qa_count < QA_PER_NOVEL:
            qa = generate_qa_batch_local(model, tokenizer, chunks, novel)
            if qa:
                all_qa_pairs.append(qa)
                novel_qa_count += 1
                pbar.update(1)
            else:
                failures += 1
                if failures > 50: # Skip if too many failures
                    print(f"  Skipping rest of {novel} due to generation errors.")
                    break
        pbar.close()
        
        # Save progress after each novel
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_qa_pairs, f, ensure_ascii=False, indent=2)
            
    print(f"Completed! Generated {len(all_qa_pairs)} QA pairs. Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
