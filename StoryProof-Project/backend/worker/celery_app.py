from celery import Celery
from backend.core.config import settings

# 앱 이름을 정의하고 Redis 연결 설정
celery_app = Celery(
    "storyproof_worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/2",

    include=[
        "backend.worker.tasks",
        "backend.services.tasks" 
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
)