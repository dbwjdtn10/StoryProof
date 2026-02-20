import json
import os
import sys
import numpy as np
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

# Debug Settings
ALPHA = 0.825 # Analyze failure at optimal alpha
NUM_FAILURES_TO_SHOW = 5

def load_qa_data(filepath: str) -> list:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_novel_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def split_text(text: str, chunk_size: int, overlap: int) -> list:
    if not text: return []
    step = chunk_size - overlap
    if step <= 0: step = 1
    chunks = []
    for i in range(0, len(text), step):
        chunks.append(text[i:i + chunk_size])
    return chunks

def normalize_scores(scores: np.ndarray) -> np.ndarray:
    if len(scores) == 0: return scores
    min_val = np.min(scores)
    max_val = np.max(scores)
    if max_val == min_val: return np.zeros_like(scores)
    return (scores - min_val) / (max_val - min_val)

def main():
    load_dotenv()
    print(f"Analyzing Failures with Alpha={ALPHA}...\n")

    qa_data = load_qa_data(BENCHMARK_FILE)
    unique_novels = list(set([qa['novel_filename'] for qa in qa_data]))
    
    # Indices
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
            all_chunk_metadata.append({"novel": filename, "text": chunk, "id": i})
            
    corpus_embeddings = model.encode(all_chunks, normalize_embeddings=True, show_progress_bar=False)
    tokenized_corpus = [chunk.split() for chunk in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    
    failure_count = 0
    
    with open("benchmark_failures.txt", "w", encoding="utf-8") as f:
        f.write(f"Analyzing Failures with Alpha={ALPHA}...\n\n")
        
        for qa in qa_data:
            question = qa['question']
            target_segment = qa.get('source_segment', '')
            answer = qa.get('answer', '')
            target_novel = qa['novel_filename']
            
            # Search
            query_embedding = model.encode(question, normalize_embeddings=True)
            dense_scores = np.dot(corpus_embeddings, query_embedding)
            
            tokenized_query = question.split()
            sparse_scores = np.array(bm25.get_scores(tokenized_query))
            
            hybrid_scores = (ALPHA * normalize_scores(dense_scores)) + \
                            ((1 - ALPHA) * normalize_scores(sparse_scores))
            
            top_indices = np.argsort(hybrid_scores)[::-1][:5]
            
            # Check Hit (Lenient)
            found = False
            
            for rank, idx in enumerate(top_indices):
                retrieved = all_chunk_metadata[idx]
                
                # Check Overlap
                if retrieved['novel'] == target_novel:
                    if target_segment and (target_segment in retrieved['text'] or retrieved['text'] in target_segment):
                        found = True; break
                    if answer and answer in retrieved['text']:
                        found = True; break
            
            if not found:
                failure_count += 1
                if failure_count <= NUM_FAILURES_TO_SHOW:
                    f.write(f"FAILURE CASE #{failure_count}\n")
                    f.write(f"Question: {question}\n")
                    f.write(f"Goal Answer: {answer}\n")
                    f.write(f"Target Segment: {target_segment[:200]}...\n")
                    f.write("-" * 20 + "\n")
                    f.write("Top-3 Retrieved:\n")
                    for i in range(3):
                        idx = top_indices[i]
                        chunk = all_chunk_metadata[idx]
                        score = hybrid_scores[idx]
                        f.write(f"  [{i+1}] Score: {score:.4f} | Novel: {chunk['novel']}\n")
                        f.write(f"      Text: {chunk['text'][:200].replace(chr(10), ' ')}...\n")
                    f.write("=" * 60 + "\n\n")

        f.write(f"\nTotal Failures shown: {min(failure_count, NUM_FAILURES_TO_SHOW)}")


if __name__ == "__main__":
    main()
