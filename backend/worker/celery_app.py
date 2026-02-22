import logging

from celery import Celery
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Celery 인스턴스 생성
celery_app = Celery(
    "storyproof_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.worker.tasks", "backend.worker.prediction_tasks"]
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


# 워커 시작 시 모델 프리로딩
from celery.signals import worker_ready

@worker_ready.connect
def preload_models(sender, **kwargs):
    """
    Celery 워커가 준비되면 AI 모델을 미리 로드합니다.
    첫 번째 태스크 실행 시 모델 로딩 지연을 방지합니다.
    """
    try:
        from backend.services.analysis import EmbeddingSearchEngine
        engine = EmbeddingSearchEngine()
        engine.warmup()
        logger.info("Celery Worker: All models preloaded successfully.")
    except Exception as e:
        logger.warning(f"Celery Worker: Model preloading failed: {e}")


if __name__ == "__main__":
    celery_app.start()
