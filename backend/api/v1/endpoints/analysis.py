"""
AI 분석 API 엔드포인트
====================
- 설정 파괴 분석 (비동기 Celery 작업) + DB 캐시
- 분석 작업 상태/결과 조회
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from celery.result import AsyncResult
from datetime import datetime

from backend.worker.tasks import detect_inconsistency_task
from backend.worker.celery_app import celery_app
from backend.core.config import settings
from backend.schemas.analysis_schema import ConsistencyRequest
from backend.db.session import get_db
from backend.db.models import Analysis, AnalysisType, AnalysisStatus

router = APIRouter()


# ===== 설정 파괴 분석 - 캐시 조회 =====

@router.get("/consistency/{novel_id}/{chapter_id}")
def get_cached_consistency(novel_id: int, chapter_id: int, db: Session = Depends(get_db)):
    """
    설정 파괴 분석 캐시 조회

    DB에서 가장 최근 COMPLETED 결과를 반환합니다.
    """
    analysis = db.query(Analysis).filter(
        Analysis.novel_id == novel_id,
        Analysis.chapter_id == chapter_id,
        Analysis.analysis_type == AnalysisType.CONSISTENCY,
        Analysis.status == AnalysisStatus.COMPLETED,
    ).order_by(Analysis.completed_at.desc()).first()

    if analysis:
        return {"cached": True, "result": analysis.result}
    return {"cached": False, "result": None}


# ===== 설정 파괴 분석 =====

@router.post("/consistency", status_code=status.HTTP_202_ACCEPTED)
def request_consistency(request: ConsistencyRequest, db: Session = Depends(get_db)):
    """
    설정 파괴 분석 비동기 요청

    Analysis 레코드를 생성하고 Celery 작업으로 비동기 처리합니다.
    """
    # Analysis 레코드 생성 (PENDING)
    analysis = Analysis(
        novel_id=request.novel_id,
        chapter_id=request.chapter_id,
        analysis_type=AnalysisType.CONSISTENCY,
        status=AnalysisStatus.PENDING,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    task = detect_inconsistency_task.delay(
        request.novel_id, request.text, request.chapter_id, analysis.id
    )
    return {"task_id": task.id, "status": "PENDING", "analysis_id": analysis.id}


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
