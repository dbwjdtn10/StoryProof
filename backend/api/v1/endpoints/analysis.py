"""
AI 분석 API 엔드포인트
====================
- 설정 파괴 분석 (비동기 Celery 작업)
- 스토리 예측 (동기 처리)
- 분석 작업 상태/결과 조회
"""

from fastapi import APIRouter, HTTPException, status
from celery.result import AsyncResult

from backend.worker.tasks import detect_inconsistency_task
from backend.worker.celery_app import celery_app
from backend.services.agent import get_consistency_agent
from backend.core.config import settings
from backend.schemas.analysis_schema import ConsistencyRequest, PredictionRequest

router = APIRouter()


# ===== 설정 파괴 분석 =====

@router.post("/consistency", status_code=status.HTTP_202_ACCEPTED)
async def request_consistency(request: ConsistencyRequest):
    """
    설정 파괴 분석 비동기 요청

    Celery 작업으로 비동기 처리되며, task_id를 반환합니다.
    결과는 GET /task/{task_id}로 조회 가능합니다.
    """
    task = detect_inconsistency_task.delay(request.novel_id, request.text, request.chapter_id)
    return {"task_id": task.id, "status": "PENDING"}


# ===== 분석 작업 결과 조회 =====

@router.get("/task/{task_id}")
async def get_task_result(task_id: str):
    """
    Celery 분석 작업 결과 조회

    Returns:
        status: COMPLETED | FAILED | PROCESSING
        result: 분석 결과 (COMPLETED 시)
        error: 에러 메시지 (FAILED 시)
    """
    result = AsyncResult(task_id, app=celery_app)
    if result.state == 'SUCCESS':
        return {"status": "COMPLETED", "result": result.result}
    elif result.state == 'FAILURE':
        return {"status": "FAILED", "error": str(result.info)}
    return {"status": "PROCESSING"}


# ===== 스토리 예측 =====

@router.post("/prediction", status_code=status.HTTP_200_OK)
def request_prediction(request: PredictionRequest):
    """
    스토리 예측 요청 (동기 처리)

    사용자의 What-If 가정을 바탕으로 스토리 전개를 예측합니다.
    FastAPI가 자동으로 threadpool에서 실행합니다.
    """
    try:
        result = get_consistency_agent().predict_story(request.novel_id, request.text)
        return {"result": result, "status": "COMPLETED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
