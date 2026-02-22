"""
Story Prediction Worker Tasks
"""
import logging
from typing import Optional
from datetime import datetime

from backend.worker.celery_app import celery_app
from backend.core.config import settings
from backend.services.agent import StoryConsistencyAgent
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(name="predict_story_task", bind=True, max_retries=2)
def predict_story_task(self, novel_id: int, user_input: str, analysis_id: Optional[int] = None):
    db = None
    try:
        # DB 상태 업데이트: PROCESSING
        if analysis_id:
            from backend.db.models import Analysis, AnalysisStatus
            db = SessionLocal()
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = AnalysisStatus.PROCESSING
                db.commit()

        agent = StoryConsistencyAgent(api_key=settings.GOOGLE_API_KEY)
        result = agent.predict_story(novel_id, user_input)

        # DB 상태 업데이트: COMPLETED + 결과 저장 (user_input 포함)
        if analysis_id and db:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = AnalysisStatus.COMPLETED
                analysis.result = {"user_input": user_input, **result}
                analysis.completed_at = datetime.utcnow()
                db.commit()

        return result
    except Exception as exc:
        # DB 상태 업데이트: FAILED
        if analysis_id:
            try:
                if not db:
                    db = SessionLocal()
                from backend.db.models import Analysis, AnalysisStatus
                analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
                if analysis:
                    analysis.status = AnalysisStatus.FAILED
                    analysis.error_message = str(exc)
                    db.commit()
            except Exception as db_exc:
                logger.warning(f"예측 실패 DB 상태 업데이트 중 오류: {db_exc}")
        logger.error(f"스토리 예측 실패: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        if db:
            db.close()
