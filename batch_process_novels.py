import os
import glob
import json
import tqdm
import sys

# Add parent directory to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from story_analyzer import DocumentLoader, SceneChunker
from sentence_transformers import SentenceTransformer

def process_novels(corpus_dir: str, output_file: str):
    """
    Process all novels in the corpus directory:
    1. Load text
    2. Chunk into scenes
    3. Generate embeddings
    4. Save to JSON
    """
    
    # 1. Setup
    print("Loading Embedding Model (BAAI/bge-m3)...")
    model = SentenceTransformer('BAAI/bge-m3')
    chunker = SceneChunker()
    
    txt_files = glob.glob(os.path.join(corpus_dir, "*.txt"))
    print(f"Found {len(txt_files)} novels in {corpus_dir}")
    
    results = []
    
    # 2. Process each file
    for file_path in tqdm.tqdm(txt_files, desc="Processing Novels"):
        filename = os.path.basename(file_path)
        print(f"\nProcessing: {filename}")
        
        # Load Text
        try:
            text = DocumentLoader.load_txt(file_path)
        except Exception as e:
            print(f"Failed to load {filename}: {e}")
            continue
            
        # Chunking
        print(f"  Chunking...")
        scenes = chunker.split_into_scenes(text)
        print(f"  {len(scenes)} scenes found.")
        
        # Embedding & Structuring
        file_data = {
            "filename": filename,
            "total_scenes": len(scenes),
            "chunks": []
        }
        
        print(f"  Generating embeddings...")
        
        # Batch embedding for efficiency
        embeddings = model.encode(scenes, normalize_embeddings=True)
        
        for idx, (scene_text, embedding) in enumerate(zip(scenes, embeddings)):
            chunk_data = {
                "scene_index": idx + 1,
                "text": scene_text,
                "embedding": embedding.tolist() # Convert numpy array to list for JSON serialization
            }
            file_data["chunks"].append(chunk_data)
            
        results.append(file_data)
        
    # 3. Save key output for verification
    print(f"\nSaving results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"Done! Processed {len(results)} novels.")

if __name__ == "__main__":
    CORPUS_DIR = "novel_corpus_kr"
    OUTPUT_FILE = "novel_embeddings.json"
    
    # Ensure absolute paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_path = os.path.join(base_dir, CORPUS_DIR)
    output_path = os.path.join(base_dir, OUTPUT_FILE)
    
    if not os.path.exists(corpus_path):
        print(f"❌ Corpus directory not found: {corpus_path}")
    else:
        process_novels(corpus_path, output_path)
