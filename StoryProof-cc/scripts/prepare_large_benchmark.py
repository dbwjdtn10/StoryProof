import os
import sys
import json
import glob
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings

# Configuration
NOVEL_DIR = "novel_corpus_kr"
OUTPUT_FILE = "large_corpus.json"
EXCLUDE_FILE = "KR_Thebrotherskaramazov.txt"
MODEL_NAME = settings.KOREAN_EMBEDDING_MODEL
CHUNK_SIZE = 500  # Explicitly set per request
CHUNK_OVERLAP = 100

def load_novel_text(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def split_text(text: str, chunk_size: int, overlap: int) -> list:
    if not text: return []
    step = chunk_size - overlap
    if step <= 0: step = 1
    chunks = []
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        if len(chunk) < 50: continue # Skip very short chunks
        chunks.append(chunk)
    return chunks

def main():
    load_dotenv()
    print(f"Preparing large benchmark corpus from {NOVEL_DIR}...")
    
    # 1. Select Novels
    exclude_path = os.path.join(NOVEL_DIR, EXCLUDE_FILE)
    all_files = glob.glob(os.path.join(NOVEL_DIR, "*.txt"))
    target_files = [f for f in all_files if os.path.abspath(f) != os.path.abspath(exclude_path)]
    
    print(f"Found {len(all_files)} files. Excluded 1. Processing {len(target_files)} novels.")
    
    # 2. Chunking
    all_chunks = []
    metadata = []
    
    for filepath in tqdm(target_files, desc="Chunking Novels"):
        filename = os.path.basename(filepath)
        text = load_novel_text(filepath)
        chunks = split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            metadata.append({
                "novel_filename": filename,
                "chunk_index": i,
                "text": chunk
            })
            
    print(f"Total Chunks: {len(all_chunks)}")
    
    # 3. Embedding
    print(f"Generating Embeddings using {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    # Encode in batches
    embeddings = model.encode(all_chunks, normalize_embeddings=True, show_progress_bar=True)
    
    # 4. Save to JSON
    # We save embeddings as list for JSON serialization
    output_data = []
    for meta, emb in zip(metadata, embeddings):
        meta['embedding'] = emb.tolist()
        output_data.append(meta)
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"Saved corpus to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
