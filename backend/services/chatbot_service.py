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
    DEFAULT_ALPHA = 0.825  # 최적화된 기본값 (Vector 82.5%, BM25 17.5%)
    DEFAULT_SIMILARITY_THRESHOLD = 0.2  # Reranker 도입으로 기준 하향 (0.5 -> 0.2)

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
                print("[Success] ChatbotService: EmbeddingSearchEngine loaded")
            except Exception as e:
                print(f"[Error] ChatbotService: Failed to load EmbeddingSearchEngine: {e}")
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
        novel_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        novel_filter: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        original_query: Optional[str] = None
    ) -> List[Dict]:
        """
        질문과 가장 유사한 씬(청크)을 Pinecone에서 검색합니다.
        """
        # 검색 엔진이 초기화되지 않은 경우 빈 리스트 반환
        if not self.engine:
            return []
            
        # Step 1: novel_filter로 소설 ID 조회 (novel_id가 직접 전달되지 않은 경우만)
        if novel_id is None and novel_filter:
            db = SessionLocal()
            try:
                # 파일명에서 확장자 제거 (예: "alice.txt" → "alice")
                search_term = novel_filter.replace('.txt', '')
                
                # 데이터베이스에서 제목으로 소설 검색 (대소문자 무시)
                novel = db.query(Novel).filter(Novel.title.ilike(f"%{search_term}%")).first()
                if novel:
                    novel_id = novel.id
                    print(f"[Search] Chatbot: Resolved novel_filter '{novel_filter}' to ID {novel_id} ({novel.title})")
                else:
                    print(f"[Warning] Chatbot: novel_filter '{novel_filter}' not found in DB")
            finally:
                db.close()
        elif novel_id:
            print(f"[Search] Chatbot: Using direct novel_id {novel_id}")
        
        # Step 2: Pinecone 벡터 검색 실행
        try:
            results = self.engine.search(
                query=question, 
                novel_id=novel_id, 
                chapter_id=chapter_id, 
                top_k=top_k,
                alpha=alpha,
                keywords=keywords,
                original_query=original_query or question
            )
            print(f"[Search] Chatbot: Found {len(results)} results (Novel: {novel_id}, Chapter Context: {chapter_id})")
            
            # Step 3: 결과 포맷 변환 및 필터링
            formatted_results = []
            for res in results:
                similarity = res['similarity']
                doc = res['document']
                scene_idx = doc.get('scene_index', '?')
                
                # 유사도가 임계값 미만이면 제외
                if similarity < similarity_threshold:
                    print(f"  - [DROP] Scene {scene_idx}: similarity {similarity:.4f} < {similarity_threshold}")
                    continue
                
                print(f"  - [KEEP] Scene {scene_idx}: similarity {similarity:.4f}")
                    
                formatted_results.append({
                    'text': doc.get('original_text', ''),
                    'scene_index': doc.get('scene_index'),
                    'chapter_id': res.get('chapter_id'),
                    'summary': doc.get('summary'),
                    'novel_id': novel_id,
                    'similarity': similarity,
                    'original_similarity': similarity
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
        # - 할루시네이션 방지: 컨텍스트 외부 지식 사용 금지
        prompt = f"""다음 문맥을 바탕으로 질문에 답변하세요.

[답변 가이드라인]
1. **제공된 문맥을 최우선으로 참고하세요.**
2. **문맥에 직접적인 정답이 없다면, 문맥의 단서들을 종합하여 가장 합리적인 답변을 추론하세요.**
3. **추론된 답변일 경우, "~로 추정됩니다" 또는 "문맥상 ~인 것으로 보입니다"와 같이 표현하세요.**
4. **답변에 [Context N]과 같은 출처 표시는 절대 포함하지 마세요.**

[답변 형식]
반드시 다음 형식을 지켜주세요. 두 섹션 사이에는 빈 줄을 두세요.

[핵심 요약]
(질문에 대한 핵심 답변을 1~2문장으로 요약)

[상세 설명]
(문맥을 바탕으로 한 구체적인 설명과 근거, 추론 내용 포함)

문맥:
{context[:3500]}
        
질문: {question}
        
답변:"""
        
        # Gemini API 호출
        # 할루시네이션 방지를 위한 생성 파라미터 설정:
        # - temperature=0.1: 낮은 온도로 일관성 및 사실성 향상
        # - top_p=0.8: 확률 분포 제한으로 예측 가능성 증가
        # - top_k=20: 후보 토큰 제한
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,  # 예: "gemini-2.5-flash"
                contents=prompt,
                config={
                    'temperature': 0.1,  # 낮은 temperature로 할루시네이션 감소
                    'top_p': 0.8,        # 확률 분포 제한
                    'top_k': 20,         # 후보 토큰 제한
                    'max_output_tokens': 1024
                }
            )
            return response.text
        except Exception as e:
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    def warmup(self):
        """
        챗봇 서비스 웜업 (엔진 모델 프리로딩)
        """
        if self.engine:
            self.engine.warmup()
        else:
            print("[Warning] ChatbotService: Engine not initialized, skipping warmup.")

    def augment_query(self, question: str) -> str:
        """
        사용자 질문을 검색에 최적화된 형태로 확장합니다.
        Gemini를 사용하여 관련 키워드, 동의어, 구체적인 표현만 추출하고, 원본 질문과 결합합니다.
        """
        if not self.client:
            return question

        prompt = f"""당신은 소설 검색 전문가입니다. 다음 질문에 대해 검색 정확도를 높이기 위한 **추가 검색 키워드**만 공백으로 구분하여 나열하세요.

[사용자 질문]
"{question}"

[확장 가이드]
1. 질문의 핵심 소재, 인물, 장소, 시간적 배경(처음, 끝 등)에 대한 관련 키워드를 추출하세요.
2. "장소"에 대해서는 "위치, 배경, 공간" 등 다양한 동의어를 추가하세요.
3. 질문에 "처음", "시작" 등이 포함되면 "최초, 등장, Scene 1" 등의 키워드를 추가하세요.
4. 질문 내용은 다시 적지 말고, **오직 추가 키워드들만** 공백으로 구분하여 한 줄로 출력하세요.

[출력 형식]
추가 키워드1 키워드2 키워드3 ... (설명 없이 키워드만)

출력:"""
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,
                contents=prompt,
                config={
                    'temperature': 0.2,
                    'max_output_tokens': 100
                }
            )
            keywords = response.text.strip()
            
            # 따옴표 제거
            keywords = keywords.strip('"').strip("'")
            
            # 원본 질문과 결합 (원본 질문 보존 보장)
            augmented = f"{question} {keywords}"
            
            print(f"[Augment] Query Expanded: '{question}' -> '{augmented}'")
            return augmented
        except Exception as e:
            print(f"[Warning] Query Augmentation Failed: {e}")
            return question
        except Exception as e:
            print(f"[Warning] Query Augmentation Failed: {e}")
            return question

    def _extract_keywords(self, text: str) -> List[str]:
        """
        텍스트에서 검색에 유용한 명사 및 핵심 키워드를 추출합니다.
        Kiwi 형태소 분석기를 사용합니다.
        """
        if not self.engine or not hasattr(self.engine, '_get_kiwi'):
            return text.split()
            
        try:
            kiwi = self.engine._get_kiwi()
            # NNG(일반 명사), NNP(고유 명사), SL(외국어) 위주로 추출
            tokens = kiwi.tokenize(text)
            keywords = [t.form for t in tokens if t.tag in ['NNG', 'NNP', 'SL'] or len(t.form) > 1]
            
            # 중복 제거 및 너무 짧은 단어 필터링 (한 글자 명사 제외 등, 상황에 따라 조절)
            unique_keywords = list(dict.fromkeys(keywords))
            print(f"[Keyword] Keywords Extracted: {unique_keywords}")
            return unique_keywords
        except Exception as e:
            print(f"[Warning] Keyword Extraction Failed: {e}")
            return text.split()

    def hybrid_search(
        self, 
        question: str, 
        novel_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        novel_filter: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        하이브리드 검색: LLM 가공 + 벡터 검색 + 키워드 검색
        """
        # 1. LLM으로 쿼리 확장
        augmented = self.augment_query(question)
        
        # 2. 확장된 쿼리에서 키워드 추출 (Sparse 검색용)
        keywords = self._extract_keywords(augmented)
        
        # 3. 통합 검색 (Dense + Sparse)
        # find_similar_chunks 내부의 engine.search가 hybrid score를 계산함
        results = self.find_similar_chunks(
            question=augmented,
            novel_id=novel_id,
            chapter_id=chapter_id,
            novel_filter=novel_filter,
            keywords=keywords,
            original_query=question,  # 리랭커를 위해 원본 질문 전달
            **kwargs
        )
        
        return results

    def ask(
        self,
        question: str,
        alpha: float = DEFAULT_ALPHA,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        novel_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        novel_filter: Optional[str] = None
    ) -> Dict:
        """
        질문에 대한 답변 생성 (전체 파이프라인)
        
        검색 전략:
        1. 하이브리드 검색 (LLM 확장 + Dense + Sparse)
        2. 실패 시 원본 쿼리로 2차 검색 (폴백)
        """
        # 1. 하이브리드 검색 실행
        print(f"[Search] 원본 질문: '{question}'")
        top_chunks = self.hybrid_search(
            question=question,
            alpha=alpha,
            similarity_threshold=similarity_threshold,
            novel_id=novel_id,
            chapter_id=chapter_id,
            novel_filter=novel_filter
        )
        
        # 2. 실패 시 원본 쿼리로 2차 검색 (폴백)
        if not top_chunks:
            print("[Warning] 하이브리드 검색 실패, 원본 쿼리로 재시도...")
            top_chunks = self.find_similar_chunks(
                question=question,  # 원본 쿼리
                top_k=5,
                alpha=alpha,
                similarity_threshold=similarity_threshold,
                novel_id=novel_id,
                chapter_id=chapter_id,
                novel_filter=novel_filter
            )

        # 3. 여전히 유사한 스토리보드가 없는 경우
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
        
        # 4. 컨텍스트 생성 (상위 청크 텍스트 결합)
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
        
        # 4. LLM으로 답변 생성
        answer = self.generate_answer(question, context)
        
        # 가장 높은 유사도 정보
        best_chunk = top_chunks[0]
        
        # novel title 가져오기
        novel_title = "Unknown Novel"
        if best_chunk.get('novel_id'):
            db = SessionLocal()
            try:
                novel = db.query(Novel).filter(Novel.id == best_chunk['novel_id']).first()
                if novel:
                    novel_title = novel.title
            finally:
                db.close()

        return {
            "answer": answer,
            "source": {
                "filename": novel_title,
                "chapter_id": best_chunk.get('chapter_id'),
                "scene_index": best_chunk.get('scene_index'),
                "summary": best_chunk.get('summary'),
                "total_scenes": len(top_chunks)
            },
            "similarity": best_chunk.get('similarity', 0.0), # similarity might be missing in some cases if not careful
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

