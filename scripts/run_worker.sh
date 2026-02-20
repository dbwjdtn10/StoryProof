#!/bin/bash
echo "Starting Celery Worker..."
echo "Make sure Redis is running! (docker-compose up -d redis)"

# Go to project root
cd ..
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run Celery
celery -A backend.worker.celery_app worker --loglevel=info
