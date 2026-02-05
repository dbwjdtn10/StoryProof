import sys
import os
import subprocess

# Ensure we are running from the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

print("Starting Celery Worker...")
print("Ensure you have a Redis server running on localhost:6379")

# Command to start celery worker
# -A backend.worker.celery_app : The application instance
# worker : The command
# --loglevel=info : Logging level
# --pool=solo : Required for Windows to function correctly without forks
cmd = [
    sys.executable, "-m", "celery", 
    "-A", "backend.worker.celery_app", 
    "worker", 
    "--loglevel=info", 
    "--pool=solo"
]

try:
    subprocess.run(cmd)
except KeyboardInterrupt:
    print("\nWorker stopped.")
except Exception as e:
    print(f"\nError running worker: {e}")
