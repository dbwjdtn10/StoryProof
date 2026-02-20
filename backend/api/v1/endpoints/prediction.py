"""
Story Prediction API Endpoints
- 스토리 예측 비동기 요청
- 대화 히스토리 DB 저장/조회/삭제
"""

from fastapi import APIRouter, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from backend.worker.celery_app import celery_app
from backend.worker.prediction_tasks import predict_story_task
from backend.db.session import get_db
from backend.db.models import Analysis, AnalysisType, AnalysisStatus

router = APIRouter()


class PredictionRequest(BaseModel):
    novel_id: int
    text: str


@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
def request_prediction(request: PredictionRequest, db: Session = Depends(get_db)):
    """
    스토리 예측 요청 (비동기 Celery)

    Analysis 레코드를 생성하고 Celery 작업으로 비동기 처리합니다.
    """
    analysis = Analysis(
        novel_id=request.novel_id,
        chapter_id=None,
        analysis_type=AnalysisType.PREDICTION,
        status=AnalysisStatus.PENDING,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    task = predict_story_task.delay(request.novel_id, request.text, analysis.id)
    return {"task_id": task.id, "status": "PENDING", "analysis_id": analysis.id}


@router.get("/task/{task_id}")
async def get_prediction_task_status(task_id: str):
    """
    예측 작업 상태 조회
    """
    result = AsyncResult(task_id, app=celery_app)
    if result.state == 'SUCCESS':
        return {"status": "COMPLETED", "result": result.result}
    elif result.state == 'FAILURE':
        return {"status": "FAILED", "error": str(result.info)}
    return {"status": "PROCESSING"}


@router.get("/history/{novel_id}")
def get_prediction_history(novel_id: int, db: Session = Depends(get_db)):
    """
    해당 소설의 prediction 대화 이력 조회

    COMPLETED 상태의 prediction Analysis 레코드를 시간순으로 반환합니다.
    각 레코드의 result에 user_input과 prediction이 포함됩니다.
    """
    analyses = db.query(Analysis).filter(
        Analysis.novel_id == novel_id,
        Analysis.analysis_type == AnalysisType.PREDICTION,
        Analysis.status == AnalysisStatus.COMPLETED,
    ).order_by(Analysis.created_at.asc()).all()

    history = []
    for a in analyses:
        if a.result:
            history.append({
                "id": a.id,
                "user_input": a.result.get("user_input", ""),
                "prediction": a.result.get("prediction", ""),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })
    return {"history": history}


@router.delete("/history/{novel_id}")
def clear_prediction_history(novel_id: int, db: Session = Depends(get_db)):
    """
    해당 소설의 prediction 대화 이력 삭제
    """
    deleted = db.query(Analysis).filter(
        Analysis.novel_id == novel_id,
        Analysis.analysis_type == AnalysisType.PREDICTION,
    ).delete()
    db.commit()
    return {"deleted": deleted}
