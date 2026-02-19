@echo off
echo Starting Celery Worker...
echo Make sure Redis is running! (docker-compose up -d redis)

cd ..
set PYTHONPATH=%PYTHONPATH%;%CD%
celery -A backend.worker.celery_app worker --loglevel=info --pool=solo
pause
