"""
Story Prediction API Endpoints
"""

from fastapi import APIRouter, status, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from backend.worker.celery_app import celery_app
from backend.worker.prediction_tasks import predict_story_task

router = APIRouter()

class PredictionRequest(BaseModel):
    novel_id: int
    text: str

@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
async def request_prediction(request: PredictionRequest):
    """
    스토리 예측 요청
    """
    # 비동기 작업 요청
    task = predict_story_task.delay(request.novel_id, request.text)
    return {"task_id": task.id, "status": "PENDING"}

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
