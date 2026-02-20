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
BENCHMARK_FILE = "benchmark_qa.json"
NOVEL_DIR = "novel_corpus_kr"
MODEL_NAME = settings.KOREAN_EMBEDDING_MODEL
CHUNK_SIZE = settings.CHILD_CHUNK_SIZE
CHUNK_OVERLAP = settings.CHILD_CHUNK_OVERLAP
OUTPUT_IMAGE = "benchmark_alpha_curve_v2.png"

def load_qa_data(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_novel_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def split_text(text: str, chunk_size: int, overlap: int) -> list:
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
    if len(scores) == 0:
        return scores
    min_val = np.min(scores)
    max_val = np.max(scores)
    if max_val - min_val == 0:
        return np.zeros_like(scores)
    return (scores - min_val) / (max_val - min_val)

def main():
    load_dotenv()
    
    # Enable Korean font support for Matplotlib if available, else fallback
    plt.rcParams['font.family'] = 'Malgun Gothic' # For Windows
    plt.rcParams['axes.unicode_minus'] = False

    print(f"Loading benchmark data from {BENCHMARK_FILE}...")
    if not os.path.exists(BENCHMARK_FILE):
        print(f"Error: {BENCHMARK_FILE} not found.")
        return

    qa_data = load_qa_data(BENCHMARK_FILE)
    unique_novels = list(set([qa['novel_filename'] for qa in qa_data]))
    
    # Prepare Indices
    print(f"Preparing indices for {len(unique_novels)} novels...")
    all_chunks = [] 
    all_chunk_metadata = []
    
    model = SentenceTransformer(MODEL_NAME)
    
    for filename in unique_novels:
        filepath = os.path.join(NOVEL_DIR, filename)
        if not os.path.exists(filepath): continue
        text = load_novel_text(filepath)
        chunks = split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_chunk_metadata.append({"novel": filename, "text": chunk})
            
    # Dense Index
    print("Encoding chunks (Dense)...")
    corpus_embeddings = model.encode(all_chunks, normalize_embeddings=True, show_progress_bar=True)
    
    # Sparse Index
    print("Building BM25 index (Sparse)...")
    tokenized_corpus = [chunk.split() for chunk in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # Evaluation Loop
    alphas = [round(a, 2) for a in np.arange(0.0, 1.05, 0.05)]
    top5_accuracies = []
    top1_accuracies = []
    soft_top5_accuracies = []
    
    print(f"\nRunning benchmark on {len(qa_data)} QA pairs...")
    
    for alpha in alphas:
        matches_top1 = 0
        matches_top5 = 0
        matches_soft_top5 = 0
        
        for qa in qa_data:
            question = qa['question']
            target_segment = qa.get('source_segment', '')
            answer = qa.get('answer', '')
            target_novel = qa['novel_filename']
            
            # Hybrid Search Simulation
            query_embedding = model.encode(question, normalize_embeddings=True)
            dense_scores = np.dot(corpus_embeddings, query_embedding)
            
            tokenized_query = question.split()
            sparse_scores = np.array(bm25.get_scores(tokenized_query))
            
            hybrid_scores = (alpha * normalize_scores(dense_scores)) + \
                            ((1 - alpha) * normalize_scores(sparse_scores))
            
            top_indices = np.argsort(hybrid_scores)[::-1][:5]
            
            found_1 = False
            found_5 = False
            found_soft_5 = False
            
            for rank, idx in enumerate(top_indices):
                retrieved = all_chunk_metadata[idx]
                
                # Default "Strict" Logic (Must be same novel + overlap)
                is_hit = False
                if retrieved['novel'] == target_novel:
                    if target_segment and (target_segment in retrieved['text'] or retrieved['text'] in target_segment):
                        is_hit = True
                    elif qa['answer'] in retrieved['text']:
                        is_hit = True
                
                if is_hit:
                    if rank == 0: found_1 = True
                    found_5 = True
                
                # "Soft" Logic (Answer Keyword Overlap)
                # If target novel matches AND significant overlap with Answer keywords
                if retrieved['novel'] == target_novel:
                    # Simple keyword extraction (space split, length > 1)
                    ans_tokens = set([t for t in answer.split() if len(t) > 1])
                    ret_tokens = set(retrieved['text'].split())
                    if len(ans_tokens) > 0:
                        overlap = len(ans_tokens.intersection(ret_tokens))
                        # If more than 50% of answer keywords are found, count as hit
                        if overlap / len(ans_tokens) >= 0.5:
                            found_soft_5 = True

            if found_1: matches_top1 += 1
            if found_5: matches_top5 += 1
            if found_soft_5: matches_soft_top5 += 1
            
        top1_acc = matches_top1 / len(qa_data)
        top5_acc = matches_top5 / len(qa_data)
        soft_top5_acc = matches_soft_top5 / len(qa_data)
        
        top1_accuracies.append(top1_acc)
        top5_accuracies.append(top5_acc)
        soft_top5_accuracies.append(soft_top5_acc)

    # Plotting
    print(f"Generating graph to {OUTPUT_IMAGE}...")
    plt.figure(figsize=(10, 6))
    plt.plot(alphas, top5_accuracies, marker='o', label='Strict Exact Match (Top-5)', color='blue')
    plt.plot(alphas, soft_top5_accuracies, marker='*', label='Soft Keyword Match (Top-5)', color='red', linestyle='--')
    plt.plot(alphas, top1_accuracies, marker='s', label='Strict Top-1', color='green', linestyle=':')
    
    plt.title('Hybrid Search Performance by Alpha (Strict vs Soft)')
    plt.xlabel('Alpha (Vector Weight)')
    plt.ylabel('Accuracy (Recall)')
    plt.ylim(0, 1.0)
    plt.grid(True)
    plt.legend()
    plt.xticks(np.arange(0, 1.1, 0.1))
    
    # Save
    plt.savefig(OUTPUT_IMAGE)
    print("Done!")

if __name__ == "__main__":
    main()
