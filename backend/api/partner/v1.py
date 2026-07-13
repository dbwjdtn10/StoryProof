"""
파트너(B2B) API v1
==================
인터넷서점/웹소설 플랫폼(교보문고, 알라딘, 카카오페이지 등) 고객사 대상 API.

- 인증: X-API-Key 헤더 (파트너별 발급)
- 테넌트 격리: 파트너의 서비스 계정(User) 소유 데이터만 접근 가능
- 모든 호출은 사용량 로그에 기록 (과금/정산 근거)

주요 흐름:
  1. POST /manuscripts        원고 접수 → 자동 청킹/구조화/임베딩 (비동기)
  2. GET  /manuscripts/{id}/status   처리 상태 폴링
  3. POST /manuscripts/{id}/qa       작품 내용 기반 Q&A (독자용 챗봇)
  4. POST /manuscripts/{id}/consistency  설정 일관성 검증 (편집자용)
  5. GET  /tasks/{task_id}    비동기 작업 결과 조회
  6. GET  /usage              이번 달 사용량 조회
"""

import logging

import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from backend.db.session import get_db
from backend.db.models import (
    Novel, Chapter, Analysis, AnalysisType, AnalysisStatus, ApiUsageLog,
)
from backend.core.partner_auth import (
    PartnerContext, get_current_partner, log_api_usage, get_partner_monthly_usage,
)
from backend.schemas.partner_schema import (
    ManuscriptCreateRequest, ManuscriptCreateResponse,
    ManuscriptStatusResponse, ChapterStatusOut,
    PartnerQARequest, PartnerQAResponse,
    ConsistencyCheckRequest, AsyncTaskResponse,
    UsageSummaryResponse,
    WebhookConfigRequest, WebhookConfigResponse, WebhookInfoResponse,
    WidgetSessionRequest, WidgetSessionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_partner_novel(db: Session, ctx: PartnerContext, manuscript_id: int) -> Novel:
    """파트너 소유 원고 조회 (테넌트 격리 강제)"""
    novel = db.query(Novel).filter(
        Novel.id == manuscript_id,
        Novel.author_id == ctx.partner.user_id,
    ).first()
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="원고를 찾을 수 없습니다.",
        )
    return novel


# ===== 원고 접수 =====

@router.post("/manuscripts", response_model=ManuscriptCreateResponse,
             status_code=status.HTTP_202_ACCEPTED)
def create_manuscript(
    request: ManuscriptCreateRequest,
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """원고 접수 및 분석 파이프라인 시작

    회차별로 청킹 → 구조 분석 → 벡터 임베딩이 백그라운드에서 진행된다.
    과금 단위: 접수 회차 수
    """
    description = request.description or ""
    if request.external_id:
        # 파트너 측 작품 ID를 설명에 태깅 (별도 컬럼 없이 매핑 유지)
        description = f"[external_id:{request.external_id}] {description}".strip()

    novel = Novel(
        title=request.title,
        description=description,
        genre=request.genre,
        author_id=ctx.partner.user_id,
        is_public=False,
    )
    db.add(novel)
    db.commit()
    db.refresh(novel)

    chapter_ids = []
    for ch in request.chapters:
        chapter = Chapter(
            novel_id=novel.id,
            chapter_number=ch.chapter_number,
            title=ch.title,
            content=ch.content,
            word_count=len(ch.content),
            storyboard_status="PENDING",
        )
        db.add(chapter)
        db.flush()
        chapter_ids.append(chapter.id)
    db.commit()

    from backend.worker.tasks import process_chapter_storyboard
    for chapter_id in chapter_ids:
        process_chapter_storyboard.delay(novel.id, chapter_id)

    log_api_usage(db, ctx, "/manuscripts", units=len(chapter_ids), status_code=202)

    return ManuscriptCreateResponse(
        manuscript_id=novel.id,
        external_id=request.external_id,
        chapter_ids=chapter_ids,
    )


@router.post("/manuscripts/upload", response_model=ManuscriptCreateResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def upload_manuscript_file(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(None),
    genre: str = Form(None),
    external_id: str = Form(None),
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """원고 파일 접수 (EPUB/TXT/DOCX/PDF)

    - EPUB: spine 문서 단위로 자동 회차 분리 (전자책 표준 워크플로)
    - TXT/DOCX/PDF: 전체를 1개 회차로 접수
    과금 단위: 생성 회차 수
    """
    from backend.core.config import settings

    filename = (file.filename or "").lower()
    ext = os.path.splitext(filename)[1]
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: {ext} (지원: {', '.join(settings.ALLOWED_EXTENSIONS)})",
        )

    # Content-Length로 명백히 큰 업로드는 본문을 메모리에 읽기 전에 거부
    # (완전한 방어는 아님 — 리버스 프록시의 body size 제한과 함께 사용할 것,
    # 2026-07-13 코드리뷰에서 발견: read()-then-check는 OOM에 취약)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기가 업로드 한도를 초과합니다.")

    raw_data = await file.read()
    if len(raw_data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기가 업로드 한도를 초과합니다.")

    # 파일 → (제목, 본문) 회차 목록
    if ext == ".epub":
        from backend.services.analysis.epub_loader import extract_epub_chapters
        try:
            parsed_chapters = extract_epub_chapters(raw_data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        from backend.services.novel_service import NovelService
        await file.seek(0)
        content = await NovelService._load_file_content(file)
        if not content.strip():
            raise HTTPException(status_code=400, detail="파일 내용이 비어있습니다.")
        parsed_chapters = [("1화", content)]

    description = ""
    if external_id:
        description = f"[external_id:{external_id}]"

    novel = Novel(
        title=title or os.path.splitext(file.filename or "untitled")[0],
        description=description,
        genre=genre,
        author_id=ctx.partner.user_id,
        is_public=False,
    )
    db.add(novel)
    db.commit()
    db.refresh(novel)

    chapter_ids = []
    for idx, (ch_title, ch_text) in enumerate(parsed_chapters, start=1):
        chapter = Chapter(
            novel_id=novel.id,
            chapter_number=idx,
            title=ch_title[:255],
            content=ch_text,
            word_count=len(ch_text),
            storyboard_status="PENDING",
        )
        db.add(chapter)
        db.flush()
        chapter_ids.append(chapter.id)
    db.commit()

    from backend.worker.tasks import process_chapter_storyboard
    for chapter_id in chapter_ids:
        process_chapter_storyboard.delay(novel.id, chapter_id)

    log_api_usage(db, ctx, "/manuscripts/upload", units=len(chapter_ids), status_code=202)

    return ManuscriptCreateResponse(
        manuscript_id=novel.id,
        external_id=external_id,
        chapter_ids=chapter_ids,
    )


@router.get("/manuscripts/{manuscript_id}/status", response_model=ManuscriptStatusResponse)
def get_manuscript_status(
    manuscript_id: int,
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """원고 처리 상태 조회 (상태 폴링은 과금하지 않음)"""
    novel = _get_partner_novel(db, ctx, manuscript_id)
    chapters = db.query(Chapter).filter(
        Chapter.novel_id == novel.id
    ).order_by(Chapter.chapter_number).all()

    chapter_statuses = [
        ChapterStatusOut(
            chapter_id=c.id,
            chapter_number=c.chapter_number,
            status=(c.storyboard_status or "PENDING"),
            progress=(c.storyboard_progress or 0),
            error=c.storyboard_error,
        )
        for c in chapters
    ]
    ready = all(s.status.upper() == "COMPLETED" for s in chapter_statuses) if chapter_statuses else False

    return ManuscriptStatusResponse(
        manuscript_id=novel.id,
        title=novel.title,
        ready=ready,
        chapters=chapter_statuses,
    )


# ===== 작품 Q&A (독자용 챗봇) =====

@router.post("/manuscripts/{manuscript_id}/qa", response_model=PartnerQAResponse)
def ask_manuscript(
    manuscript_id: int,
    request: PartnerQARequest,
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """작품 내용 기반 RAG Q&A

    chapter_id 지정 시 해당 회차까지의 내용만 사용 → 독자가 읽은 지점까지만
    답변하는 스포일러 방지 챗봇 구현 가능.
    과금 단위: 질문 1건
    """
    novel = _get_partner_novel(db, ctx, manuscript_id)

    from backend.services.chatbot_service import get_chatbot_service
    result = get_chatbot_service().ask(
        question=request.question,
        alpha=0.7,
        similarity_threshold=0.2,
        novel_id=novel.id,
        chapter_id=request.chapter_id,
        novel_filter=None,
        db=db,
    )

    log_api_usage(db, ctx, "/manuscripts/qa", units=1, status_code=200)

    return PartnerQAResponse(
        answer=result.get("answer", ""),
        found_context=result.get("found_context", False),
        similarity=result.get("similarity", 0.0),
    )


# ===== 설정 일관성 검증 (편집자용) =====

@router.post("/manuscripts/{manuscript_id}/consistency",
             response_model=AsyncTaskResponse,
             status_code=status.HTTP_202_ACCEPTED)
def check_consistency(
    manuscript_id: int,
    request: ConsistencyCheckRequest,
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """설정 일관성 검증 (비동기)

    - chapter_id 지정: 등록된 해당 회차 원고를 기존 설정과 대조
    - text 지정: 등록 전 신규 원고를 기존 설정과 대조 (연재 검수 워크플로)
    과금 단위: 검증 1건
    """
    novel = _get_partner_novel(db, ctx, manuscript_id)

    text = request.text
    chapter_id = request.chapter_id
    if not text:
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id 또는 text가 필요합니다.")
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == novel.id,
        ).first()
        if not chapter:
            raise HTTPException(status_code=404, detail="회차를 찾을 수 없습니다.")
        text = chapter.content

    analysis = Analysis(
        novel_id=novel.id,
        chapter_id=chapter_id,
        analysis_type=AnalysisType.CONSISTENCY,
        status=AnalysisStatus.PENDING,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    from backend.worker.tasks import detect_inconsistency_task
    task = detect_inconsistency_task.delay(novel.id, text, chapter_id, analysis.id)

    log_api_usage(db, ctx, "/manuscripts/consistency", units=1, status_code=202)

    return AsyncTaskResponse(task_id=task.id)


# ===== 비동기 작업 결과 =====

@router.get("/tasks/{task_id}")
def get_task_result(
    task_id: str,
    ctx: PartnerContext = Depends(get_current_partner),
):
    """비동기 작업(일관성 검증 등) 결과 조회 (과금하지 않음)"""
    from backend.worker.celery_app import celery_app
    result = AsyncResult(task_id, app=celery_app)
    if result.state == "SUCCESS":
        return {"status": "COMPLETED", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "FAILED", "error": str(result.info)}
    return {"status": "PROCESSING"}


# ===== 위젯 세션 =====

@router.post("/widget-sessions", response_model=WidgetSessionResponse)
def create_widget_session(
    request: WidgetSessionRequest,
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """임베드 위젯용 단기 세션 토큰 발급 (파트너 서버에서 호출)

    발급된 토큰을 위젯 `<script>` 태그의 data-token으로 전달하면,
    브라우저는 API 키 없이 해당 작품 범위의 Q&A만 호출할 수 있다.
    chapter_id를 지정하면 위젯 답변이 해당 회차까지로 제한된다 (스포일러 방지).
    토큰 발급 자체는 과금하지 않음 (위젯 Q&A 호출 시 과금).
    """
    from backend.core.widget_auth import create_widget_session_token

    novel = _get_partner_novel(db, ctx, request.manuscript_id)

    token, expires_in = create_widget_session_token(
        partner_id=ctx.partner.id,
        manuscript_id=novel.id,
        chapter_id=request.chapter_id,
        ttl_minutes=request.ttl_minutes,
    )
    return WidgetSessionResponse(
        token=token,
        expires_in=expires_in,
        manuscript_id=novel.id,
        chapter_id=request.chapter_id,
    )


# ===== 웹훅 설정 =====

@router.put("/webhook", response_model=WebhookConfigResponse)
def configure_webhook(
    request: WebhookConfigRequest,
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """웹훅 URL 등록/변경

    등록하면 원고 처리/분석 완료 이벤트가 이 URL로 POST 전송된다
    (폴링 불필요). 응답의 secret은 이 응답에서만 확인 가능하며,
    수신 측에서 `X-StoryProof-Signature` 헤더를 HMAC-SHA256으로 검증할 때 사용한다.
    """
    import secrets as _secrets

    partner = ctx.partner
    partner.webhook_url = request.url
    partner.webhook_secret = _secrets.token_hex(32)
    db.commit()

    return WebhookConfigResponse(url=request.url, secret=partner.webhook_secret)


@router.get("/webhook", response_model=WebhookInfoResponse)
def get_webhook_config(
    ctx: PartnerContext = Depends(get_current_partner),
):
    """웹훅 설정 조회 (secret은 노출하지 않음)"""
    return WebhookInfoResponse(
        url=ctx.partner.webhook_url,
        configured=bool(ctx.partner.webhook_url and ctx.partner.webhook_secret),
    )


@router.delete("/webhook", status_code=status.HTTP_204_NO_CONTENT)
def remove_webhook(
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """웹훅 해제 (이후 이벤트는 전송되지 않음)"""
    partner = ctx.partner
    partner.webhook_url = None
    partner.webhook_secret = None
    db.commit()


# ===== 사용량 조회 =====

@router.get("/usage", response_model=UsageSummaryResponse)
def get_usage_summary(
    ctx: PartnerContext = Depends(get_current_partner),
    db: Session = Depends(get_db),
):
    """이번 달 사용량 요약 (정산 확인용, 과금하지 않음)"""
    used = get_partner_monthly_usage(db, ctx.partner.id)

    return UsageSummaryResponse(
        partner_name=ctx.partner.name,
        plan=ctx.partner.plan,
        monthly_quota=ctx.partner.monthly_quota,
        used_this_month=int(used),
        remaining=max(0, ctx.partner.monthly_quota - int(used)),
    )
