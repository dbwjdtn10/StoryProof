import json
import os
import sys
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings

# Configuration
CORPUS_FILE = "large_corpus.json"
QA_FILE = "large_benchmark_qa.json"
MODEL_NAME = settings.KOREAN_EMBEDDING_MODEL
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
ALPHA = 0.83
QA_LIMIT = None # Full benchmark

def load_data(filepath: str) -> list:
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
    print("Loading Data...")
    corpus_data = load_data(CORPUS_FILE)
    qa_data = load_data(QA_FILE)
    if not corpus_data or not qa_data: return

    # Limit for speed
    if QA_LIMIT and len(qa_data) > QA_LIMIT:
        print(f"Limiting QA pairs to {QA_LIMIT} for speed...")
        import random
        random.seed(42)
        qa_data = random.sample(qa_data, QA_LIMIT)
    
    # 1. Prepare Hybrid Search (Baseline)
    corpus_texts = [item['text'] for item in corpus_data]
    
    # Reuse embeddings if available
    if 'embedding' in corpus_data[0]:
        print("Using pre-calculated embeddings...")
        corpus_embeddings = np.array([item['embedding'] for item in corpus_data])
    else:
        print("Calculating corpus embeddings...")
        model = SentenceTransformer(MODEL_NAME)
        corpus_embeddings = model.encode(corpus_texts, normalize_embeddings=True, show_progress_bar=True)
        
    print("Building BM25 Index...")
    tokenized_corpus = [doc.split() for doc in corpus_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    
    print("Encoding Queries...")
    model = SentenceTransformer(MODEL_NAME)
    questions = [qa['question'] for qa in qa_data]
    query_embeddings = model.encode(questions, normalize_embeddings=True, show_progress_bar=True)
    
    # 2. Hybrid Search (Alpha=0.83) -> Top 50 Candidates
    print(f"Running Hybrid Search (Alpha={ALPHA}) to get Top-50 candidates...")
    
    # Calc scores
    dense_scores_all = np.dot(query_embeddings, corpus_embeddings.T)
    sparse_scores_all = np.zeros((len(qa_data), len(corpus_data)))
    for i, q in enumerate(questions):
        sparse_scores_all[i] = bm25.get_scores(q.split())
        
    # Normalize & Fuse
    candidates_list = [] # List of (question, [candidate_indices])
    
    for i in tqdm(range(len(qa_data)), desc="Hybrid Retrieval"):
        d_scores = normalize_scores(dense_scores_all[i])
        s_scores = normalize_scores(sparse_scores_all[i])
        h_scores = (ALPHA * d_scores) + ((1 - ALPHA) * s_scores)
        
        # Get Top-50
        top_50_indices = np.argpartition(h_scores, -50)[-50:]
        # Sort them by score desc
        top_50_indices = top_50_indices[np.argsort(h_scores[top_50_indices])[::-1]]
        
        candidates_list.append(top_50_indices)

    # Clean up memory before Reranker
    del model
    del query_embeddings
    del dense_scores_all
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 3. Reranking
    print(f"Loading Reranker: {RERANKER_MODEL}...")
    reranker = CrossEncoder(RERANKER_MODEL, max_length=512)
    
    hits_hybrid_top5 = 0
    hits_rerank_top5 = 0
    
    print("Reranking candidates...")
    
    for i, qa in enumerate(tqdm(qa_data, desc="Reranking")):
        question = qa['question']
        target_novel = qa['novel_filename']
        answer = qa['answer']
        ans_tokens = set([t for t in answer.split() if len(t) > 1])
        
        # Hybrid Top-5 Check
        candidates_indices = candidates_list[i]
        hybrid_top5_indices = candidates_indices[:5]
        
        found_hybrid = False
        for idx in hybrid_top5_indices:
            retrieved = corpus_data[idx]
            if retrieved['novel_filename'] == target_novel:
                ret_tokens = set(retrieved['text'].split())
                if len(ans_tokens) > 0 and len(ans_tokens.intersection(ret_tokens)) / len(ans_tokens) >= 0.5:
                    found_hybrid = True
                    break
        if found_hybrid: hits_hybrid_top5 += 1
        
        # Prepare pairs for Reranker: (Question, Candidate_Text)
        canidate_pairs = [[question, corpus_data[idx]['text']] for idx in candidates_indices]
        
        # Predict scores
        rerank_scores = reranker.predict(canidate_pairs)
        
        # Re-sort Top-50 based on Reranker scores
        # rerank_scores is list of floats
        # sort candidates_indices based on rerank_scores desc
        sorted_indices_local = np.argsort(rerank_scores)[::-1]
        reranked_global_indices = [candidates_indices[j] for j in sorted_indices_local]
        
        # Rerank Top-5 Check
        rerank_top5_indices = reranked_global_indices[:5]
        found_rerank = False
        for idx in rerank_top5_indices:
            retrieved = corpus_data[idx]
            if retrieved['novel_filename'] == target_novel:
                ret_tokens = set(retrieved['text'].split())
                if len(ans_tokens) > 0 and len(ans_tokens.intersection(ret_tokens)) / len(ans_tokens) >= 0.5:
                    found_rerank = True
                    break
        if found_rerank: hits_rerank_top5 += 1
        
    acc_hybrid = hits_hybrid_top5 / len(qa_data)
    acc_rerank = hits_rerank_top5 / len(qa_data)
    
    print("\n" + "="*50)
    print("RERANKER BENCHMARK RESULTS")
    print("="*50)
    print(f"Baseline (Hybrid Top-5) Accuracy: {acc_hybrid:.4f} ({hits_hybrid_top5}/{len(qa_data)})")
    print(f"Reranked (Top-50 -> Top-5) Accuracy: {acc_rerank:.4f} ({hits_rerank_top5}/{len(qa_data)})")
    print("-" * 50)
    print(f"Improvement: +{(acc_rerank - acc_hybrid)*100:.2f}%p")
    print("="*50)

if __name__ == "__main__":
    main()
