import json
import os
import numpy as np
from rank_bm25 import BM25Okapi
from tqdm import tqdm
from kiwipiepy import Kiwi
from dotenv import load_dotenv

load_dotenv()

# Configuration
BENCHMARK_DIR = "benchmark"
CORPUS_FILE = os.path.join(BENCHMARK_DIR, "large_corpus.json")
QA_FILE = os.path.join(BENCHMARK_DIR, "large_benchmark_qa.json")
OUTPUT_FILE = os.path.join(BENCHMARK_DIR, "kiwi_benchmark_result.txt")

def load_data():
    print("Loading corpus...")
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        corpus_data = json.load(f)
    
    print("Loading QA data...")
    with open(QA_FILE, 'r', encoding='utf-8') as f:
        qa_data = json.load(f)
        
    return corpus_data, qa_data

def whitespace_tokenizer(text):
    return text.split()

def main():
    corpus_data, qa_data = load_data()
    
    # 1. Prepare Corpus Text
    corpus_texts = [doc['text'] for doc in corpus_data]
    
    # --- Benchmark 1: Whitespace Tokenizer (Baseline) ---
    print("\n[Baseline] Tokenizing with Whitespace...")
    tokenized_corpus_ws = [whitespace_tokenizer(doc) for doc in tqdm(corpus_texts)]
    bm25_ws = BM25Okapi(tokenized_corpus_ws)
    
    print("Benchmarking Whitespace BM25 (Recall@50)...")
    hits_ws = 0
    
    for qa in tqdm(qa_data):
        query = qa['question']
        target_novel = qa['novel_filename']
        answer = qa['answer']
        
        tokenized_query = whitespace_tokenizer(query)
        scores = bm25_ws.get_scores(tokenized_query)
        top_n_indices = np.argsort(scores)[::-1][:50]
        
        # Check if answer is in top 50
        ans_tokens = set([t for t in answer.split() if len(t) > 1])
        if not ans_tokens: continue
            
        found = False
        for idx in top_n_indices:
            retrieved = corpus_data[idx]
            if retrieved['novel_filename'] == target_novel:
                ret_tokens = set(retrieved['text'].split())
                if len(ans_tokens.intersection(ret_tokens)) / len(ans_tokens) >= 0.5:
                    found = True
                    break
        if found:
            hits_ws += 1
            
    recall_ws = hits_ws / len(qa_data)
    print(f"Whitespace Recall@50: {recall_ws:.4f}")
    
    # --- Benchmark 2: Kiwi Tokenizer ---
    print("\n[Experiment] Tokenizing with Kiwi...")
    kiwi = Kiwi()
    
    # Kiwi Tokenizer Helper
    def kiwi_tokenizer(text):
        return [t.form for t in kiwi.tokenize(text)]

    tokenized_corpus_kiwi = []
    print("Tokenizing Corpus with Kiwi (This may take a while)...")
    for doc in tqdm(corpus_texts):
        tokenized_corpus_kiwi.append(kiwi_tokenizer(doc))
        
    bm25_kiwi = BM25Okapi(tokenized_corpus_kiwi)
    
    print("Benchmarking Kiwi BM25 (Recall@50)...")
    hits_kiwi = 0
    
    for qa in tqdm(qa_data):
        query = qa['question']
        target_novel = qa['novel_filename']
        answer = qa['answer']
        
        tokenized_query = kiwi_tokenizer(query)
        scores = bm25_kiwi.get_scores(tokenized_query)
        top_n_indices = np.argsort(scores)[::-1][:50]
        
        # Check if answer is in top 50
        ans_tokens = set([t for t in answer.split() if len(t) > 1])
        if not ans_tokens: continue
            
        found = False
        for idx in top_n_indices:
            retrieved = corpus_data[idx]
            if retrieved['novel_filename'] == target_novel:
                ret_tokens = set(retrieved['text'].split())
                if len(ans_tokens.intersection(ret_tokens)) / len(ans_tokens) >= 0.5:
                    found = True
                    break
        if found:
            hits_kiwi += 1
            
    recall_kiwi = hits_kiwi / len(qa_data)
    print(f"Kiwi Recall@50: {recall_kiwi:.4f}")
    
    # Report
    improvement = recall_kiwi - recall_ws
    report = f"""
    [Benchmark Result] BM25 Tokenizer Comparison
    ---------------------------------------------
    Baseline (Whitespace) Recall@50: {recall_ws:.4f}
    Experiment (Kiwi)     Recall@50: {recall_kiwi:.4f}
    ---------------------------------------------
    Improvement: {improvement:+.4f} ({improvement*100:+.2f}%)
    """
    print(report)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    main()
