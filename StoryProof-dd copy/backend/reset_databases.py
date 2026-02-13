
import sys
import os
import time

# Add project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.db.session import reset_db
from backend.core.config import settings
from pinecone import Pinecone

def reset_postgresql():
    print("Resetting PostgreSQL database...")
    try:
        reset_db()
        print("PostgreSQL database reset successfully.")
    except Exception as e:
        print(f"Failed to reset PostgreSQL database: {e}")

def reset_pinecone():
    print("Resetting Pinecone index...")
    api_key = settings.PINECONE_API_KEY
    index_name = settings.PINECONE_INDEX_NAME
    
    if not api_key:
        print("Pinecone API Key not found. Skipping Pinecone reset.")
        return

    try:
        pc = Pinecone(api_key=api_key)
        
        # Check if index exists
        indexes = pc.list_indexes()
        index_names = [i.name for i in indexes]
        
        if index_name in index_names:
            index = pc.Index(index_name)
            # Delete all vectors in the index
            # Note: delete_all=True clears the default namespace. 
            # If namespaces are used, we might need to iterate or delete specific namespaces.
            # Assuming default namespace or 'delete_all' clears everything for now.
            index.delete(delete_all=True)
            print(f"Pinecone index '{index_name}' cleared successfully.")
        else:
            print(f"Pinecone index '{index_name}' not found.")
            
    except Exception as e:
        print(f"Failed to reset Pinecone index: {e}")

if __name__ == "__main__":
    print("Starting database reset...")
    reset_postgresql()
    reset_pinecone()
    print("Database reset complete.")
