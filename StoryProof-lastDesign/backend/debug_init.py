
import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

print("Attempting to import EmbeddingSearchEngine...")
try:
    from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
    print("Import successful.")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

print("Initializing EmbeddingSearchEngine...")
try:
    engine = EmbeddingSearchEngine()
    print("Initialization successful.")
except Exception as e:
    print(f"Initialization failed: {e}")
    # Don't exit, try to see if it was Pinecone
    
print("Running warmup...")
try:
    engine.warmup()
    print("Warmup successful.")
except Exception as e:
    print(f"Warmup failed: {e}")
