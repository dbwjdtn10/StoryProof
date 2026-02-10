# backend/worker/celery_app.py
from celery import Celery
import os

# 환경 변수 설정 (필요시)
os.environ.setdefault('FORKED_BY_CELERY', '1')

from backend.core.config import settings

celery_app = Celery(
    "storyproof_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['backend.worker.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
)