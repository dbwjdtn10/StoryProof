import sys
import os
import uvicorn

print("=== Environment Debug Info ===")
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
try:
    import celery
    print(f"Celery Version: {celery.__version__}")
    print(f"Celery Location: {celery.__file__}")
except ImportError as e:
    print(f"ERROR: Could not import celery: {e}")
    sys.exit(1)

try:
    import redis
    print(f"Redis Version: {redis.__version__}")
except ImportError:
    print("WARNING: Could not import redis")

print("==============================")
print("Starting Uvicorn programmatically...")

if __name__ == "__main__":
    # Add project root to sys.path just in case
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
