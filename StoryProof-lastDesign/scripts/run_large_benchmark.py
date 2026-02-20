import json
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings

# Configuration
CORPUS_FILE = "large_corpus.json"
QA_FILE = "large_benchmark_qa.json"
OUTPUT_IMAGE = "large_benchmark_result.png"
MODEL_NAME = settings.KOREAN_EMBEDDING_MODEL

def load_data(filepath: str) -> list:
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_scores(scores: np.ndarray) -> np.ndarray:
    if len(scores) == 0: return scores
    min_val = np.min(scores)
    max_val = np.max(scores)
    if max_val - min_val == 0:
        return np.zeros_like(scores)
    return (scores - min_val) / (max_val - min_val)

def main():
    load_dotenv()
    
    # Enable Korean font
    plt.rcParams['font.family'] = 'Malgun Gothic' 
    plt.rcParams['axes.unicode_minus'] = False

    print(f"Loading Corpus: {CORPUS_FILE}")
    corpus_data = load_data(CORPUS_FILE)
    if not corpus_data: return

    print(f"Loading QA: {QA_FILE}")
    qa_data = load_data(QA_FILE)
    if not qa_data: return
    
    # Extract Embeddings and Text
    print("Preparing Indices...")
    corpus_texts = [item['text'] for item in corpus_data]
    # Check if embeddings are pre-calculated
    if 'embedding' in corpus_data[0]:
        print("Using pre-calculated embeddings...")
        corpus_embeddings = np.array([item['embedding'] for item in corpus_data])
    else:
        print("Calculating embeddings (this might take a while)...")
        model = SentenceTransformer(MODEL_NAME)
        corpus_embeddings = model.encode(corpus_texts, normalize_embeddings=True, show_progress_bar=True)

    # Build Sparse Index
    print("Building BM25 Index...")
    tokenized_corpus = [doc.split() for doc in corpus_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Pre-calculate query embeddings to save time in loop
    print("Encoding Queries...")
    model = SentenceTransformer(MODEL_NAME)
    questions = [qa['question'] for qa in qa_data]
    query_embeddings = model.encode(questions, normalize_embeddings=True, show_progress_bar=True)
    
    # Benchmark Loop
    alphas = [round(a, 2) for a in np.arange(0.00, 1.01, 0.01)]
    
    strict_accs = []
    soft_accs = []
    
    print(f"Running benchmark on {len(qa_data)} QA pairs with {len(alphas)} alpha steps...")
    
    # We can optimize by pre-calculating all dense/sparse scores for all queries?
    # Memory usage might be high if Corpus is huge (15 novels * 500 chars).
    # 15 novels * ~200KB = ~3MB text. 
    # Approx 6000 chunks. 
    # 1500 queries.
    # Score matrix: 1500 x 6000 (Float32) ~= 36MB. Fits in memory easily.
    
    print("Pre-calculating score matrices...")
    
    # Dense Scores: (Num_Queries, Num_Chunks)
    dense_score_matrix = np.dot(query_embeddings, corpus_embeddings.T)
    
    # Sparse Scores: We calculate on the fly or pre-calc? 
    # BM25 is fast enough but 1500 queries x 6000 docs is ok.
    # Let's pre-calc sparse scores too for speed.
    sparse_score_matrix = np.zeros((len(qa_data), len(corpus_data)))
    
    for i, q in enumerate(tqdm(questions, desc="Sparse Scores")):
        sparse_score_matrix[i] = bm25.get_scores(q.split())
        
    # Normalize per query row
    print("Normalizing scores...")
    for i in range(len(qa_data)):
        dense_score_matrix[i] = normalize_scores(dense_score_matrix[i])
        sparse_score_matrix[i] = normalize_scores(sparse_score_matrix[i])
        
    print("Iterating Alphas...")
    
    for alpha in tqdm(alphas, desc="Alpha Loop"):
        # Hybrid Matrix
        hybrid_matrix = (alpha * dense_score_matrix) + ((1 - alpha) * sparse_score_matrix)
        
        # Get Top-5 Indices
        # argpartition is faster than argsort for top-k
        top_k_indices = np.argpartition(hybrid_matrix, -5, axis=1)[:, -5:]
        
        match_strict = 0
        match_soft = 0
        
        for i, qa in enumerate(qa_data):
            target_novel = qa['novel_filename']
            answer = qa['answer']
            ans_tokens = set([t for t in answer.split() if len(t) > 1])
            
            # Check the top 5 retrieved chunks
            found_strict = False
            found_soft = False
            
            for idx in top_k_indices[i]:
                retrieved = corpus_data[idx]
                
                # Strict Logic
                if retrieved['novel_filename'] == target_novel:
                    if qa.get('source_segment') and qa.get('source_segment') in retrieved['text']:
                        found_strict = True
                    elif answer in retrieved['text']:
                        found_strict = True
                        
                # Soft Logic
                if retrieved['novel_filename'] == target_novel:
                    ret_tokens = set(retrieved['text'].split())
                    if len(ans_tokens) > 0:
                        overlap = len(ans_tokens.intersection(ret_tokens))
                        if overlap / len(ans_tokens) >= 0.5:
                            found_soft = True
                            
            if found_strict: match_strict += 1
            if found_soft: match_soft += 1
            
        strict_accs.append(match_strict / len(qa_data))
        soft_accs.append(match_soft / len(qa_data))

    # Plotting
    print(f"Generating high-res graph to {OUTPUT_IMAGE}...")
    plt.figure(figsize=(12, 8), dpi=150)
    plt.plot(alphas, strict_accs, label='Strict Accuracy (Exact Match)', color='blue', linewidth=1.5)
    plt.plot(alphas, soft_accs, label='Soft Accuracy (Keyword Match)', color='red', linewidth=1.5, linestyle='--')
    
    # Find Peaks
    max_strict = max(strict_accs)
    max_strict_alpha = alphas[strict_accs.index(max_strict)]
    
    max_soft = max(soft_accs)
    max_soft_alpha = alphas[soft_accs.index(max_soft)]
    
    plt.axvline(x=max_soft_alpha, color='gray', linestyle=':', alpha=0.5, label=f'Best Soft Alpha: {max_soft_alpha}')
    
    plt.title(f'Large-Scale Hybrid Search Benchmark (N={len(qa_data)})')
    plt.xlabel('Alpha')
    plt.ylabel('Top-5 Accuracy')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.minorticks_on()
    
    plt.savefig(OUTPUT_IMAGE)
    print(f"Done! Best Soft Alpha: {max_soft_alpha} (Acc: {max_soft:.4f})")

if __name__ == "__main__":
    main()
