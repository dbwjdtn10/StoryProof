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
OUTPUT_IMAGE = "benchmark_per_novel.png"
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
    plt.rcParams['font.family'] = 'Malgun Gothic' 
    plt.rcParams['axes.unicode_minus'] = False

    print("Loading Data...")
    corpus_data = load_data(CORPUS_FILE)
    qa_data = load_data(QA_FILE)
    
    if not corpus_data or not qa_data: return
    
    # 1. Prepare Embeddings
    corpus_texts = [item['text'] for item in corpus_data]
    if 'embedding' in corpus_data[0]:
        print("Using pre-calculated corpus embeddings...")
        corpus_embeddings = np.array([item['embedding'] for item in corpus_data])
    else:
        print("Calculating corpus embeddings...")
        model = SentenceTransformer(MODEL_NAME)
        corpus_embeddings = model.encode(corpus_texts, normalize_embeddings=True, show_progress_bar=True)

    # 2. Build Sparse Index
    print("Building BM25 Index...")
    tokenized_corpus = [doc.split() for doc in corpus_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    
    # 3. Encode Queries
    print("Encoding Queries...")
    model = SentenceTransformer(MODEL_NAME)
    questions = [qa['question'] for qa in qa_data]
    query_embeddings = model.encode(questions, normalize_embeddings=True, show_progress_bar=True)
    
    # 4. Pre-calculate Scores
    print("Pre-calculating scores...")
    dense_score_matrix = np.dot(query_embeddings, corpus_embeddings.T)
    sparse_score_matrix = np.zeros((len(qa_data), len(corpus_data)))
    for i, q in enumerate(tqdm(questions, desc="Sparse Scores")):
        sparse_score_matrix[i] = bm25.get_scores(q.split())
        
    # Normalize
    for i in range(len(qa_data)):
        dense_score_matrix[i] = normalize_scores(dense_score_matrix[i])
        sparse_score_matrix[i] = normalize_scores(sparse_score_matrix[i])

    # 5. Group by Novel
    novels = sorted(list(set([qa['novel_filename'] for qa in qa_data])))
    print(f"Analyzing {len(novels)} novels...")
    
    qa_by_novel = {novel: [] for novel in novels}
    for i, qa in enumerate(qa_data):
        qa_by_novel[qa['novel_filename']].append(i) # Store index
        
    alphas = [round(a, 2) for a in np.arange(0.0, 1.05, 0.05)]
    results_per_novel = {novel: [] for novel in novels}
    average_results = []

    # 6. Benchmark Loop
    for alpha in tqdm(alphas, desc="Alpha Loop"):
        hybrid_matrix = (alpha * dense_score_matrix) + ((1 - alpha) * sparse_score_matrix)
        
        # Calculate per novel
        current_alpha_avgs = []
        
        for novel in novels:
            indices = qa_by_novel[novel] # Indices of QAs for this novel
            if not indices: continue
            
            novel_hits = 0
            
            # For each question in this novel
            for q_idx in indices:
                # Get Top-5 for this question
                scores = hybrid_matrix[q_idx]
                top_indices = np.argpartition(scores, -5)[-5:]
                
                qa = qa_data[q_idx]
                target_novel = qa['novel_filename']
                answer = qa['answer']
                ans_tokens = set([t for t in answer.split() if len(t) > 1])
                
                found = False
                for idx in top_indices:
                    retrieved = corpus_data[idx]
                    
                    if retrieved['novel_filename'] == target_novel:
                        # Soft Match Logic
                        ret_tokens = set(retrieved['text'].split())
                        if len(ans_tokens) > 0:
                            overlap = len(ans_tokens.intersection(ret_tokens))
                            if overlap / len(ans_tokens) >= 0.5:
                                found = True
                
                if found: novel_hits += 1
            
            acc = novel_hits / len(indices)
            results_per_novel[novel].append(acc)
            current_alpha_avgs.append(acc)
            
        average_results.append(np.mean(current_alpha_avgs))

    # 7. Plotting
    print(f"Generating graph to {OUTPUT_IMAGE}...")
    plt.figure(figsize=(14, 8), dpi=150)
    
    # Plot individual novels (Thin lines)
    for novel in novels:
        plt.plot(alphas, results_per_novel[novel], linewidth=1, alpha=0.4, label=novel)
        
    # Plot Average (Thick line)
    plt.plot(alphas, average_results, linewidth=4, color='black', label='AVERAGE', marker='o')
    
    plt.title('Hybrid Search Accuracy by Novel (Variance Analysis)')
    plt.xlabel('Alpha')
    plt.ylabel('Top-5 Accuracy (Soft Match)')
    plt.ylim(0, 1.0)
    plt.grid(True, alpha=0.3)
    
    # Legend handling - maybe too many?
    # Put legend outside
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    plt.tight_layout()
    
    plt.savefig(OUTPUT_IMAGE)
    print("Done!")

if __name__ == "__main__":
    main()
