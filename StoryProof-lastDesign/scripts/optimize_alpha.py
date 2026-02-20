import json
import os
import sys
import numpy as np
from typing import List, Dict, Tuple
from tqdm import tqdm
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings

# Configuration
BENCHMARK_FILE = "benchmark_qa.json"
NOVEL_DIR = "novel_corpus_kr"
MODEL_NAME = settings.KOREAN_EMBEDDING_MODEL # "dragonkue/multilingual-e5-small-ko"
CHUNK_SIZE = settings.CHILD_CHUNK_SIZE
CHUNK_OVERLAP = settings.CHILD_CHUNK_OVERLAP

def load_qa_data(filepath: str) -> List[Dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_novel_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple sliding window chunking"""
    if not text:
        return []
    step = chunk_size - overlap
    if step <= 0: step = 1
    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if len(chunk) < 50: continue
        chunks.append(chunk)
    return chunks

def normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Min-Max Normalization to 0-1 range"""
    if len(scores) == 0:
        return scores
    min_val = np.min(scores)
    max_val = np.max(scores)
    if max_val - min_val == 0:
        return np.zeros_like(scores)
    return (scores - min_val) / (max_val - min_val)

def main():
    load_dotenv()
    
    # 1. Load Data
    print(f"Loading benchmark data from {BENCHMARK_FILE}...")
    if not os.path.exists(BENCHMARK_FILE):
        print(f"Error: {BENCHMARK_FILE} not found. Run generate_benchmark_qa.py first.")
        return

    qa_data = load_qa_data(BENCHMARK_FILE)
    unique_novels = list(set([qa['novel_filename'] for qa in qa_data]))
    
    # 2. Prepare Corpus & Indices (Dense + Sparse)
    print(f"Preparing indices for {len(unique_novels)} novels...")
    
    # Global containers for all chunks from all novels
    all_chunks = [] 
    all_chunk_metadata = [] # stores (novel_filename, chunk_index, text)
    
    # Load Model
    print(f"Loading embedding model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    for filename in unique_novels:
        filepath = os.path.join(NOVEL_DIR, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filename} not found.")
            continue
            
        text = load_novel_text(filepath)
        # Use a subset of text if needed to match QA generation scope, 
        # but better to use full text to test retrieval in large corpus
        chunks = split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_chunk_metadata.append({
                "novel": filename,
                "chunk_index": i,
                "text": chunk
            })
            
    print(f"Total Chunks: {len(all_chunks)}")
    
    # Build Dense Index (Embeddings)
    print("Encoding chunks (Dense)...")
    corpus_embeddings = model.encode(all_chunks, normalize_embeddings=True, show_progress_bar=True)
    
    # Build Sparse Index (BM25)
    print("Building BM25 index (Sparse)...")
    tokenized_corpus = [chunk.split() for chunk in all_chunks] # Simple whitespace tokenization for Korean might be weak but acceptable for baseline
    bm25 = BM25Okapi(tokenized_corpus)
    
    # 3. Optimization Loop
    alphas = [round(a, 2) for a in np.arange(0.0, 1.05, 0.05)]
    results = {alpha: {"top_1": 0, "top_5": 0, "mrr": 0.0} for alpha in alphas}
    
    print(f"\nRunning calibration with {len(qa_data)} QA pairs...")
    
    for qa in tqdm(qa_data):
        question = qa['question']
        target_segment = qa.get('source_segment', '') # The golden answer text segment
        target_novel = qa['novel_filename']
        
        # 1. Dense Search
        query_embedding = model.encode(question, normalize_embeddings=True)
        dense_scores = np.dot(corpus_embeddings, query_embedding) # Cosine similarity
        
        # 2. Sparse Search
        tokenized_query = question.split()
        sparse_scores = np.array(bm25.get_scores(tokenized_query))
        
        # Normalize
        dense_scores_norm = normalize_scores(dense_scores)
        sparse_scores_norm = normalize_scores(sparse_scores)
        
        # Hybrid Search for each alpha
        for alpha in alphas:
            alpha = round(alpha, 2)
            hybrid_scores = (alpha * dense_scores_norm) + ((1 - alpha) * sparse_scores_norm)
            
            # Get Top K indices
            top_k_indices = np.argsort(hybrid_scores)[::-1][:5]
            
            # Evaluation: Is the correct chunk in Top K?
            # We check if the 'target_segment' is contained in the retrieved chunk
            # or if the retrieved chunk is from the correct novel and contains significant overlap
            
            # Simplified check: Containment
            found_1 = False
            found_5 = False
            rank = 0
            
            for rank_idx, idx in enumerate(top_k_indices):
                retrieved_doc = all_chunk_metadata[idx]
                retrieved_text = retrieved_doc['text']
                
                # Check 1: Same Novel
                if retrieved_doc['novel'] != target_novel:
                    continue
                
                # Check 2: Content Match (Fuzzy)
                # Since QA generation might have used a slightly different segmentation,
                # we check if a significant part of target_segment is in retrieved_text or vice-versa
                # Simple heuristic: 30% overlap of characters or key phrase match
                
                # Removing strict check for now, let's assume if it contains the answer it's good.
                # But we don't know the exact answer location.
                # Let's use the 'source_segment' provided by Gemini if available.
                
                is_hit = False
                if target_segment and (target_segment in retrieved_text or retrieved_text in target_segment):
                    is_hit = True
                elif not target_segment:
                    # Fallback: if answer is short, check if answer is in text
                    if qa['answer'] in retrieved_text:
                        is_hit = True
                        
                if is_hit:
                    if rank_idx == 0:
                        found_1 = True
                    found_5 = True
                    rank = 1.0 / (rank_idx + 1)
                    break
            
            results[alpha]["top_1"] += 1 if found_1 else 0
            results[alpha]["top_5"] += 1 if found_5 else 0
            results[alpha]["mrr"] += rank

    # 4. Report
    print("\noptimization Results:")
    print(f"{'Alpha':<10} | {'Top-1':<10} | {'Top-5':<10} | {'MRR':<10}")
    print("-" * 46)
    
    best_alpha = 0.0
    best_score = 0.0
    
    for alpha in alphas:
        alpha = round(alpha, 2)
        top1_acc = results[alpha]["top_1"] / len(qa_data)
        top5_acc = results[alpha]["top_5"] / len(qa_data)
        mrr = results[alpha]["mrr"] / len(qa_data)
        
        print(f"{alpha:<10} | {top1_acc:.4f}     | {top5_acc:.4f}     | {mrr:.4f}")
        
        # Metric to optimize: Top-5 Recall or MRR
        if top5_acc > best_score:
            best_score = top5_acc
            best_alpha = alpha
            
    print("-" * 46)
    print(f"✅ Best Alpha (by Top-5 Recall): {best_alpha}")

if __name__ == "__main__":
    main()
