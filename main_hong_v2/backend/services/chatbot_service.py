"""
챗봇 서비스 모듈
==============
RAG (Retrieval-Augmented Generation) 기반 소설 질의응답 시스템

주요 기능:
1. 벡터 유사도 검색 (Pinecone + BGE-M3 임베딩)
2. 컨텍스트 기반 답변 생성 (Google Gemini)
3. 소설별 필터링 지원

동작 흐름:
사용자 질문 → 임베딩 변환 → Pinecone 검색 → 유사 씬 추출 → Gemini 답변 생성
"""

from typing import Dict, List, Optional

from google import genai
from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.services.analysis import EmbeddingSearchEngine


class ChatbotService:
    """
    RAG 기반 챗봇 서비스
    
    이 클래스는 소설 텍스트에 대한 질의응답을 처리합니다.
    사용자의 질문을 임베딩으로 변환하여 Pinecone에서 유사한 씬을 검색하고,
    검색된 컨텍스트를 바탕으로 Gemini LLM이 답변을 생성합니다.
    
    Attributes:
        engine (EmbeddingSearchEngine): Pinecone 기반 벡터 검색 엔진
        client (genai.Client): Google Gemini API 클라이언트
        DEFAULT_ALPHA (float): 검색 가중치 (레거시, 현재 미사용)
        DEFAULT_SIMILARITY_THRESHOLD (float): 최소 유사도 임계값
    """
    
    # 기본 설정값 (클래스 상수)
    DEFAULT_ALPHA = 0.297  # 레거시 파라미터 (Pinecone에서는 미사용)
    DEFAULT_SIMILARITY_THRESHOLD = 0.5  # 유사도 0.5 미만은 필터링

    def __init__(self):
        """
        챗봇 서비스 초기화
        
        초기화 과정:
        1. EmbeddingSearchEngine 로드 (Pinecone 연결 + BGE-M3 모델 로드)
        2. Google Gemini API 클라이언트 설정
        
        Note:
            - 환경 변수 GOOGLE_API_KEY, PINECONE_API_KEY가 필요합니다
            - 초기화 실패 시에도 서비스는 생성되지만 기능이 제한됩니다
        """
        # Step 1: 벡터 검색 엔진 초기화
        # EmbeddingSearchEngine은 Pinecone 연결 및 BGE-M3 모델을 로드합니다
        if EmbeddingSearchEngine:
            try:
                self.engine = EmbeddingSearchEngine()
                print("✅ ChatbotService: EmbeddingSearchEngine loaded")
            except Exception as e:
                print(f"❌ ChatbotService: Failed to load EmbeddingSearchEngine: {e}")
                self.engine = None
        else:
            self.engine = None
        
        # Step 2: Google Gemini API 클라이언트 설정
        # 답변 생성을 위한 LLM 클라이언트 초기화
        if settings.GOOGLE_API_KEY:
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        else:
            self.client = None
            print("Warning: GOOGLE_API_KEY not set. LLM functionality will be disabled.")
    
    def find_similar_chunks(
        self,
        question: str,
        top_k: int = 5,
        alpha: float = DEFAULT_ALPHA,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        novel_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        질문과 가장 유사한 씬(청크)을 Pinecone에서 검색합니다.
        
        동작 과정:
        1. 질문을 BGE-M3 모델로 임베딩 벡터로 변환
        2. Pinecone에서 코사인 유사도 기반 검색
        3. novel_filter가 있으면 특정 소설로 필터링
        4. similarity_threshold 이상인 결과만 반환
        
        Args:
            question (str): 사용자 질문 (예: "주인공의 이름은?")
            top_k (int): 반환할 최대 결과 개수 (기본값: 5)
            alpha (float): 레거시 파라미터, 현재 미사용 (호환성 유지용)
            similarity_threshold (float): 최소 유사도 (0.0~1.0, 기본값: 0.5)
            novel_filter (Optional[str]): 소설 제목 또는 파일명으로 필터링
                                         (예: "alice", "KR_fantasy_alice")
            
        Returns:
            List[Dict]: 유사한 씬 목록, 각 딕셔너리는 다음 키를 포함:
                - text (str): 씬의 원본 텍스트
                - filename (str): 소설 제목 또는 요약
                - similarity (float): 유사도 점수 (0.0~1.0)
                - scene_index (int): 씬 번호
                - summary (str): 씬 요약
                
        Example:
            >>> service = ChatbotService()
            >>> results = service.find_similar_chunks(
            ...     question="앨리스는 어디로 떨어졌나요?",
            ...     top_k=3,
            ...     novel_filter="alice"
            ... )
            >>> print(f"찾은 씬 개수: {len(results)}")
        """
        # 검색 엔진이 초기화되지 않은 경우 빈 리스트 반환
        if not self.engine:
            return []
            
        # Step 1: novel_filter로 소설 ID 조회
        # 특정 소설 내에서만 검색하고 싶을 때 사용
        novel_id = None
        if novel_filter:
            db = SessionLocal()
            try:
                # 파일명에서 확장자 제거 (예: "alice.txt" → "alice")
                search_term = novel_filter.replace('.txt', '')
                
                # 데이터베이스에서 제목으로 소설 검색 (대소문자 무시)
                novel = db.query(Novel).filter(Novel.title.ilike(f"%{search_term}%")).first()
                if novel:
                    novel_id = novel.id
            finally:
                db.close()
        
        # Step 2: Pinecone 벡터 검색 실행
        # EmbeddingSearchEngine.search()는 다음을 수행:
        # 1. 질문을 BGE-M3로 임베딩 변환
        # 2. Pinecone에서 유사 벡터 검색
        # 3. PostgreSQL에서 메타데이터 조회
        try:
            results = self.engine.search(query=question, novel_id=novel_id, top_k=top_k)
            
            # Step 3: 결과 포맷 변환 및 필터링
            formatted_results = []
            for res in results:
                similarity = res['similarity']
                
                # 유사도가 임계값 미만이면 제외
                if similarity < similarity_threshold:
                    continue
                    
                doc = res['document']
                formatted_results.append({
                    'text': doc.get('original_text', ''),
                    'filename': doc.get('summary', 'Unknown'), # summary를 filename 대신 사용하거나 메타데이터에서 찾음
                    'similarity': similarity,
                    'original_similarity': similarity,
                    # 추가 메타데이터
                    'scene_index': doc.get('scene_index'),
                    'summary': doc.get('summary')
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def generate_answer(self, question: str, context: str) -> str:
        """
        Google Gemini를 사용하여 질문에 대한 답변을 생성합니다.
        
        RAG (Retrieval-Augmented Generation) 방식:
        1. 검색된 씬들을 컨텍스트로 제공
        2. Gemini가 컨텍스트를 참고하여 답변 생성
        3. 컨텍스트에 정보가 부족하면 LLM의 지식 활용
        
        프롬프트 구조:
        - 역할 정의: 소설 내용을 바탕으로 답변하는 어시스턴트
        - 답변 형식: [핵심 요약] + [상세 설명] 2단 구조
        - 컨텍스트: 검색된 씬들 (최대 3,500자)
        
        Args:
            question (str): 사용자 질문
            context (str): 검색된 씬들의 텍스트 (여러 씬이 결합된 형태)
            
        Returns:
            str: 생성된 답변 (마크다운 형식)
                 형식: [핵심 요약]\n...\n\n[상세 설명]\n...
                 
        Example:
            >>> service = ChatbotService()
            >>> context = "앨리스는 토끼를 따라 구멍으로 떨어졌다..."
            >>> answer = service.generate_answer(
            ...     question="앨리스는 어디로 떨어졌나요?",
            ...     context=context
            ... )
            >>> print(answer)
        """
        # Gemini 클라이언트가 초기화되지 않은 경우
        if not self.client:
            return "LLM이 설정되지 않았습니다. GOOGLE_API_KEY를 확인해주세요."
        
        # 프롬프트 구성
        # - 컨텍스트는 3,500자로 제한 (Gemini 토큰 제한 고려)
        # - 답변 형식을 명확히 지정하여 일관된 출력 유도
        prompt = f"""다음 문맥을 바탕으로 질문에 답변하세요.
문맥은 소설의 여러 부분에서 발췌된 내용입니다. 문맥에 정답이 없거나 부족하다면, 당신이 알고 있는 소설의 지식을 동원하여 구체적이고 풍부하게 답변해주세요.

[답변 형식]
반드시 다음 형식을 지켜주세요. 두 섹션 사이에는 빈 줄을 두세요.

[핵심 요약]
(질문에 대한 핵심 답변을 1~2문장으로 요약)

[상세 설명]
(찾은 문맥을 바탕으로 한 구체적인 설명과 근거)

문맥:
{context[:3500]}
        
질문: {question}
        
답변:"""
        
        # Gemini API 호출
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,  # 예: "gemini-2.5-flash"
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    def ask(
        self,
        question: str,
        alpha: float = DEFAULT_ALPHA,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        novel_filter: Optional[str] = None
    ) -> Dict:
        """
        질문에 대한 답변 생성 (전체 파이프라인)
        
        Args:
            question: 사용자 질문
            alpha: 가중치
            similarity_threshold: 유사도 임계값
            novel_filter: 소설 필터
            
        Returns:
            Dict: 답변 및 메타데이터
        """
        # 1. 유사한 상위 청크 찾기 (Top 5)
        top_chunks = self.find_similar_chunks(
            question=question,
            top_k=5,
            alpha=alpha,
            similarity_threshold=similarity_threshold,
            novel_filter=novel_filter
        )
        
        # 2. 유사한 스토리보드가 없는 경우
        if not top_chunks:
            error_msg = "죄송합니다. 관련 내용을 찾을 수 없습니다."
            if not self.engine:
                error_msg += " (검색 엔진이 초기화되지 않았습니다)"
            
            return {
                "answer": error_msg,
                "source": None,
                "similarity": 0.0,
                "found_context": False
            }
        
        # 3. 컨텍스트 생성 (상위 청크 텍스트 결합)
        context_texts = []
        for i, chunk in enumerate(top_chunks):
            # 씬 번호나 요약이 있으면 포함
            header = f"[Context {i+1}]"
            if chunk.get('scene_index') is not None:
                header += f" Scene {chunk['scene_index']}"
            if chunk.get('summary'):
                header += f" (Summary: {chunk['summary']})"
                
            context_texts.append(f"{header}\n{chunk['text']}")
        
        context = "\n\n".join(context_texts)
        
        # 가장 높은 유사도 정보
        best_chunk = top_chunks[0]
        
        # 4. LLM으로 답변 생성
        answer = self.generate_answer(question, context)
        
        return {
            "answer": answer,
            "source": {
                "filename": best_chunk.get('filename') or f"Scene {best_chunk.get('scene_index')}",
                "scene_index": best_chunk.get('scene_index'),
                "total_scenes": len(top_chunks)
            },
            "similarity": best_chunk['similarity'],
            "found_context": True
        }


# 싱글톤 인스턴스
_chatbot_service = None


def get_chatbot_service() -> ChatbotService:
    """
    챗봇 서비스 싱글톤 인스턴스 반환
    
    Returns:
        ChatbotService: 챗봇 서비스 인스턴스
    """
    global _chatbot_service
    if _chatbot_service is None:
        _chatbot_service = ChatbotService()
    return _chatbot_service

