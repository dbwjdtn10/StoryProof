"""
위젯 공개 API v1
================
파트너 사이트에 임베드된 챗봇 위젯이 브라우저에서 직접 호출하는 API.

- 인증: 위젯 세션 토큰 (Bearer) — 파트너 서버가 발급, 작품/회차 범위 고정
- 파트너 API 키는 브라우저에 절대 노출되지 않음
- 사용량은 토큰의 파트너에게 귀속 (쿼터/레이트 리밋 동일 적용)
- CORS: 임의의 파트너 도메인에서 호출되므로 main.py에서
  /api/widget/* 경로에 한해 Access-Control-Allow-Origin: * 허용
  (쿠키를 쓰지 않는 Bearer 토큰 인증이므로 안전)
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import Novel, ApiUsageLog
from backend.core.widget_auth import WidgetContext, get_widget_context
from backend.schemas.partner_schema import WidgetQARequest, WidgetQAResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/qa", response_model=WidgetQAResponse)
def widget_qa(
    request: WidgetQARequest,
    ctx: WidgetContext = Depends(get_widget_context),
    db: Session = Depends(get_db),
):
    """위젯 Q&A — 토큰에 고정된 작품(및 회차 상한) 범위에서만 답변

    과금 단위: 질문 1건 (토큰의 파트너에게 귀속)
    """
    from backend.services.chatbot_service import get_chatbot_service

    result = get_chatbot_service().ask(
        question=request.question,
        alpha=0.7,
        similarity_threshold=0.2,
        novel_id=ctx.manuscript_id,
        chapter_id=ctx.chapter_id,  # 토큰의 회차 상한 강제 (클라이언트가 변경 불가)
        novel_filter=None,
        db=db,
    )

    # 사용량 기록 (api_key_id 없음 — 위젯 세션 경유)
    try:
        db.add(ApiUsageLog(
            partner_id=ctx.partner.id,
            api_key_id=None,
            endpoint="/widget/qa",
            method="POST",
            units=1,
            status_code=200,
        ))
        db.commit()
    except Exception as e:
        logger.error(f"위젯 사용량 로깅 실패 (partner={ctx.partner.id}): {e}")
        db.rollback()

    return WidgetQAResponse(
        answer=result.get("answer", ""),
        found_context=result.get("found_context", False),
        similarity=result.get("similarity", 0.0),
    )


@router.get("/meta")
def widget_meta(
    ctx: WidgetContext = Depends(get_widget_context),
    db: Session = Depends(get_db),
):
    """위젯 헤더 표시용 작품 메타 정보 (무과금)"""
    novel = db.query(Novel).filter(Novel.id == ctx.manuscript_id).first()
    return {
        "manuscript_id": ctx.manuscript_id,
        "title": novel.title if novel else "",
        "chapter_id": ctx.chapter_id,
    }
