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

from fastapi import APIRouter

from backend.schemas.chat_schema import (
    ChatQuestionRequest, ChatAnswerResponse
)
from backend.services.chatbot_service import get_chatbot_service


router = APIRouter()


# ===== 챗봇 Q&A =====

@router.post("/ask", response_model=ChatAnswerResponse)
async def ask_question(
    request: ChatQuestionRequest
):
    """
    챗봇에게 질문하기
    
    RAG (Retrieval-Augmented Generation) 방식으로 답변을 생성합니다:
    1. 질문을 임베딩으로 변환
    2. Pinecone에서 유사한 씬 검색
    3. 검색된 컨텍스트를 바탕으로 Gemini가 답변 생성
    
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
            
    Example:
        ```json
        POST /api/v1/chat/ask
        {
            "question": "주인공의 이름은 무엇인가요?",
            "novel_filter": "alice",
            "similarity_threshold": 0.5
        }
        ```
        
    Raises:
        HTTPException: 검색 엔진 또는 LLM 오류 발생 시
    """
    chatbot = get_chatbot_service()
    
    result = chatbot.ask(
        question=request.question,
        alpha=request.alpha,
        similarity_threshold=request.similarity_threshold,
        novel_id=request.novel_id,
        chapter_id=request.chapter_id,
        novel_filter=request.novel_filter
    )
    
    return ChatAnswerResponse(**result)
