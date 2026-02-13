from celery import Celery
from backend.core.config import settings

# Celery 인스턴스 생성
celery_app = Celery(
    "storyproof_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.worker.tasks"]
)

# 기본 설정 업데이트
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1시간
)

if __name__ == "__main__":
    celery_app.start()
