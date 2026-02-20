"""
Q&A 채팅 API 엔드포인트
====================
소설에 대한 질의응답 기능을 제공합니다.

주요 기능:
- RAG 기반 질의응답 (/ask)
- 벡터 검색 + LLM 답변 생성

Note:
    채팅방 세션 관리 기능은 향후 구현 예정입니다.
"""

import asyncio
import json
from functools import partial

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.schemas.chat_schema import (
    ChatQuestionRequest, ChatAnswerResponse
)
from backend.services.chatbot_service import get_chatbot_service


router = APIRouter()


# ===== 챗봇 Q&A =====

@router.post("/ask", response_model=ChatAnswerResponse)
async def ask_question(
    request: ChatQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    챗봇에게 질문하기

    RAG (Retrieval-Augmented Generation) 방식으로 답변을 생성합니다:
    1. 질문을 임베딩으로 변환
    2. Pinecone에서 유사한 씬 검색
    3. 검색된 컨텍스트를 바탕으로 Gemini가 답변 생성
    4. (Method C) novel_id가 있으면 바이블 요약을 LLM 프롬프트에 주입

    Args:
        request (ChatQuestionRequest): 질문 요청
            - question (str): 사용자 질문
            - novel_filter (Optional[str]): 특정 소설로 필터링
            - alpha (float): 검색 가중치 (레거시, 기본값: 0.297)
            - similarity_threshold (float): 최소 유사도 (기본값: 0.5)

    Returns:
        ChatAnswerResponse: 답변 및 메타데이터
            - answer (str): 생성된 답변
            - source (dict): 출처 정보 (파일명, 씬 번호 등)
            - similarity (float): 최고 유사도 점수
            - found_context (bool): 컨텍스트 발견 여부

    Raises:
        HTTPException: 검색 엔진 또는 LLM 오류 발생 시
    """
    chatbot = get_chatbot_service()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        partial(
            chatbot.ask,
            question=request.question,
            alpha=request.alpha,
            similarity_threshold=request.similarity_threshold,
            novel_id=request.novel_id,
            chapter_id=request.chapter_id,
            novel_filter=request.novel_filter,
            db=db
        )
    )
    return ChatAnswerResponse(**result)


@router.post("/ask/stream")
async def ask_question_stream(
    request: ChatQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    챗봇 Q&A 스트리밍 (SSE)

    검색은 동기적으로 수행하고, LLM 답변을 Server-Sent Events로 스트리밍합니다.
    이벤트 형식:
      data: {"type": "meta", "source": ..., "similarity": ..., "found_context": true}
      data: {"type": "token", "text": "..."}
      data: [DONE]
    """
    chatbot = get_chatbot_service()
    loop = asyncio.get_running_loop()

    # 1. 검색 + 컨텍스트 준비 (동기, thread에서)
    ctx = await loop.run_in_executor(
        None,
        partial(
            chatbot._prepare_context,
            question=request.question,
            alpha=request.alpha,
            similarity_threshold=request.similarity_threshold,
            novel_id=request.novel_id,
            chapter_id=request.chapter_id,
            novel_filter=request.novel_filter,
            db=db
        )
    )

    # 2. SSE 스트리밍 제너레이터
    async def generate():
        # 메타데이터 먼저 전송
        yield f"data: {json.dumps({'type': 'meta', 'source': ctx.get('source'), 'similarity': ctx.get('similarity', 0.0), 'found_context': ctx['found_context']})}\n\n"

        if not ctx["found_context"]:
            yield f"data: {json.dumps({'type': 'token', 'text': '죄송합니다. 관련 내용을 찾을 수 없습니다.'})}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Gemini 스트리밍: 동기 → 비동기 변환 (Queue 사용)
        queue: asyncio.Queue = asyncio.Queue()

        def _run_stream():
            try:
                for token in chatbot.stream_answer(request.question, ctx["context"], ctx["bible"]):
                    asyncio.run_coroutine_threadsafe(queue.put(token), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(e), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(None, _run_stream)

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                yield f"data: {json.dumps({'type': 'error', 'text': str(item)})}\n\n"
                break
            yield f"data: {json.dumps({'type': 'token', 'text': item})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
