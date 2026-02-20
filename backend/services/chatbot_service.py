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

import time
import threading
import logging
from typing import Dict, List, Optional

from google import genai
from backend.core.config import settings

logger = logging.getLogger(__name__)
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.services.analysis import EmbeddingSearchEngine, get_embedding_search_engine


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
    
    # 기본 설정값 (settings에서 로드)
    DEFAULT_ALPHA = settings.SEARCH_DEFAULT_ALPHA
    DEFAULT_SIMILARITY_THRESHOLD = settings.SEARCH_DEFAULT_SIMILARITY_THRESHOLD

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
        try:
            self.engine = get_embedding_search_engine()
            logger.info("[Success] ChatbotService: EmbeddingSearchEngine loaded (singleton)")
        except Exception as e:
            logger.error(f"[Error] ChatbotService: Failed to load EmbeddingSearchEngine: {e}")
            self.engine = None

        # Step 2: Google Gemini API 클라이언트 설정
        # 답변 생성을 위한 LLM 클라이언트 초기화
        if settings.GOOGLE_API_KEY:
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        else:
            self.client = None
            logger.warning("GOOGLE_API_KEY not set. LLM functionality will be disabled.")

        self._augment_cache_ttl = 3600  # 1시간
        self._cache_max_size = 500  # 캐시 최대 항목 수

        # multi-query 캐시 (키: question, 값: (queries_list, timestamp))
        self._multi_query_cache: Dict[str, tuple] = {}

        # 소설 제목 인메모리 캐시 (novel_id → title)
        self._novel_title_cache: Dict[int, str] = {}
    
    def _get_novel_title(self, novel_id: int) -> str:
        """소설 제목 조회 (인메모리 캐시, 최대 50건)."""
        if novel_id in self._novel_title_cache:
            return self._novel_title_cache[novel_id]
        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            title = novel.title if novel else "Unknown Novel"
        finally:
            db.close()
        if len(self._novel_title_cache) >= 50:
            # 캐시 절반 제거
            keys = list(self._novel_title_cache.keys())
            for k in keys[:len(keys) // 2]:
                del self._novel_title_cache[k]
        self._novel_title_cache[novel_id] = title
        return title

    def _trim_cache(self, cache: Dict[str, tuple]) -> None:
        """캐시 크기가 최대치를 초과하면 만료 항목 제거 후, 여전히 초과 시 가장 오래된 절반 제거."""
        if len(cache) <= self._cache_max_size:
            return
        now = time.time()
        # 1차: 만료된 항목 제거
        expired = [k for k, v in cache.items() if (now - v[1]) >= self._augment_cache_ttl]
        for k in expired:
            del cache[k]
        # 2차: 여전히 초과 시 가장 오래된 절반 제거
        if len(cache) > self._cache_max_size:
            sorted_keys = sorted(cache.keys(), key=lambda k: cache[k][1])
            for k in sorted_keys[:len(cache) // 2]:
                del cache[k]

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
                    logger.info(f"[Search] Chatbot: Resolved novel_filter '{novel_filter}' to ID {novel_id} ({novel.title})")
                else:
                    logger.warning(f"[Search] Chatbot: novel_filter '{novel_filter}' not found in DB. 크로스 소설 검색 방지를 위해 검색을 중단합니다.")
                    return []
            finally:
                db.close()
        elif novel_id:
            logger.debug(f"[Search] Chatbot: Using direct novel_id {novel_id}")
        else:
            # novel_id도 novel_filter도 없으면 크로스 소설 검색이 발생하므로 차단
            logger.warning("[Search] Chatbot: novel_id와 novel_filter가 모두 없습니다. 크로스 소설 검색 방지를 위해 검색을 중단합니다.")
            return []
        
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
            logger.info(f"[Search] Chatbot: Found {len(results)} results (Novel: {novel_id}, Chapter Context: {chapter_id})")

            # Step 3: 결과 포맷 변환 및 필터링
            formatted_results = []
            for res in results:
                similarity = res['similarity']
                doc = res['document']
                scene_idx = doc.get('scene_index', '?')

                # 유사도가 임계값 미만이면 제외
                if similarity < similarity_threshold:
                    logger.debug(f"  - [DROP] Scene {scene_idx}: similarity {similarity:.4f} < {similarity_threshold}")
                    continue

                logger.debug(f"  - [KEEP] Scene {scene_idx}: similarity {similarity:.4f}")
                    
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
            
        except RuntimeError as e:
            # Pinecone 연결 실패 등 명시적 에러
            logger.error(f"검색 엔진 오류 (복구 불가): {e}")
            return []
        except Exception as e:
            logger.error(f"검색 중 예기치 않은 오류: {e}", exc_info=True)
            return []
    
    def _build_rag_prompt(self, question: str, context: str, bible: str = "") -> str:
        """RAG Q&A 프롬프트 구성 (generate_answer/stream_answer 공유)."""
        bible_block = f"\n\n[소설 바이블 (등장인물/관계/사건)]:\n{bible}" if bible else ""
        return f"""당신은 소설 내용 전용 질의응답 시스템입니다.
반드시 아래 [소설 문맥]에 있는 내용만 사용하여 답변하세요.

[핵심 규칙]
1. **[소설 문맥]에 있는 정보만 사용하세요. 사전 학습 지식, 추론, 상상은 절대 사용하지 마세요.**
2. **[소설 문맥]에 답이 없으면 반드시 "소설에서 해당 내용을 찾을 수 없습니다."라고만 답하세요. 일반 지식이나 추측으로 채우지 마세요.**
3. **[Context N]과 같은 출처 표시는 포함하지 마세요.**

[답변 형식]
두 섹션 사이에는 빈 줄을 두세요.

[핵심 요약]
(소설 문맥에서 찾은 핵심 답변을 1~2문장으로 요약. 문맥에 없으면 "찾을 수 없습니다."로 시작)

[상세 설명]
(소설 문맥에 있는 구체적인 내용과 근거만 서술){bible_block}

[소설 문맥]:
{context[:settings.SEARCH_CONTEXT_MAX_CHARS]}

질문: {question}

답변:"""

    _LLM_CONFIG = {
        'temperature': settings.GEMINI_RESPONSE_TEMPERATURE,
        'top_p': settings.GEMINI_RESPONSE_TOP_P,
        'top_k': settings.GEMINI_RESPONSE_TOP_K,
        'max_output_tokens': 1024,
    }

    def generate_answer(self, question: str, context: str, bible: str = "") -> str:
        """Google Gemini로 RAG 답변 생성. Method C: bible 주입."""
        if not self.client:
            return "LLM이 설정되지 않았습니다. GOOGLE_API_KEY를 확인해주세요."
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,
                contents=self._build_rag_prompt(question, context, bible),
                config=self._LLM_CONFIG,
            )
            return response.text
        except Exception as e:
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"

    def stream_answer(self, question: str, context: str, bible: str = ""):
        """Gemini 스트리밍으로 답변을 텍스트 청크 단위로 yield (동기 제너레이터)."""
        if not self.client:
            yield "LLM이 설정되지 않았습니다."
            return
        try:
            for chunk in self.client.models.generate_content_stream(
                model=settings.GEMINI_CHAT_MODEL,
                contents=self._build_rag_prompt(question, context, bible),
                config=self._LLM_CONFIG,
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"오류: {str(e)}"

    def _prepare_context(
        self,
        question: str,
        alpha: float = DEFAULT_ALPHA,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        novel_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        novel_filter: Optional[str] = None,
        db=None
    ) -> Dict:
        """검색 + 컨텍스트 준비. 스트리밍 엔드포인트에서 분리 사용."""
        top_chunks = self.hybrid_search(
            question=question, alpha=alpha, similarity_threshold=similarity_threshold,
            novel_id=novel_id, chapter_id=chapter_id, novel_filter=novel_filter
        )
        if not top_chunks:
            lowered = max(similarity_threshold - 0.1, 0.0)
            top_chunks = self.find_similar_chunks(
                question=question, top_k=settings.SEARCH_DEFAULT_TOP_K, alpha=alpha,
                similarity_threshold=lowered,
                novel_id=novel_id, chapter_id=chapter_id, novel_filter=novel_filter
            )
        if not top_chunks:
            return {"found_context": False, "context": "", "source": None, "similarity": 0.0, "bible": ""}

        context_texts = []
        for i, chunk in enumerate(top_chunks):
            header = f"[Context {i+1}]"
            if chunk.get('scene_index') is not None:
                header += f" Scene {chunk['scene_index']}"
            if chunk.get('summary'):
                header += f" (Summary: {chunk['summary']})"
            context_texts.append(f"{header}\n{chunk['text']}")
        context = "\n\n".join(context_texts)

        best_chunk = top_chunks[0]
        novel_title = self._get_novel_title(best_chunk['novel_id']) if best_chunk.get('novel_id') else "Unknown Novel"

        bible_summary = ""
        if db and novel_id:
            try:
                from backend.services.analysis_service import AnalysisService
                bible_summary = AnalysisService.get_bible_summary(db, novel_id, chapter_id)
            except Exception as e:
                logger.warning(f"바이블 요약 조회 실패 (novel={novel_id}): {e}")

        return {
            "found_context": True,
            "context": context,
            "source": {
                "filename": novel_title,
                "chapter_id": best_chunk.get('chapter_id'),
                "scene_index": best_chunk.get('scene_index'),
                "summary": best_chunk.get('summary'),
                "total_scenes": len(top_chunks)
            },
            "similarity": best_chunk.get('similarity', 0.0),
            "bible": bible_summary
        }

    def warmup(self):
        """
        챗봇 서비스 웜업 (엔진 모델 프리로딩)
        """
        if self.engine:
            self.engine.warmup()
        else:
            logger.warning("[Warning] ChatbotService: Engine not initialized, skipping warmup.")

    def _generate_multi_queries(self, question: str) -> List[str]:
        """
        한 번의 LLM 호출로 원본 질문을 3가지 다른 검색 쿼리로 변환합니다.
        각 쿼리는 다른 관점/어휘를 사용하여 검색 재현율(recall)을 극대화합니다.
        TTL 캐시 적용.
        """
        # 캐시 확인
        now = time.time()
        cached = self._multi_query_cache.get(question)
        if cached and (now - cached[1]) < self._augment_cache_ttl:
            logger.info(f"[MultiQuery] Cache hit: '{question}'")
            return cached[0]

        if not self.client:
            return [question]

        prompt = f"""당신은 소설 검색 시스템의 쿼리 최적화 전문가입니다.
사용자의 질문을 검색 엔진에서 관련 장면을 더 잘 찾을 수 있도록 3가지 다른 검색 쿼리로 변환하세요.

[사용자 질문]
"{question}"

[변환 규칙]
1번: 원본 질문의 핵심 키워드를 유지하면서 동의어와 관련 키워드를 추가하여 확장
2번: 질문의 의도를 다른 어휘와 표현으로 재구성
3번: 답이 포함될 소설 장면의 특징(인물 행동, 대사, 상황)을 묘사하는 형태로 변환

[출력 형식]
각 쿼리를 한 줄씩, 번호 없이 출력하세요. 설명은 쓰지 마세요.

출력:"""
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,
                contents=prompt,
                config={'temperature': 0.3, 'max_output_tokens': 300}
            )
            lines = [l.strip().lstrip('0123456789.-) ') for l in response.text.strip().split('\n') if l.strip()]
            queries = [l for l in lines if len(l) > 3][:3]

            if not queries:
                queries = [question]

            # 캐시 저장 (크기 제한)
            self._trim_cache(self._multi_query_cache)
            self._multi_query_cache[question] = (queries, now)
            logger.info(f"[MultiQuery] '{question}' → {len(queries)} queries generated")
            for i, q in enumerate(queries):
                logger.info(f"  Query {i+1}: {q}")
            return queries
        except Exception as e:
            logger.warning(f"[MultiQuery] Generation failed: {e}")
            return [question]

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
            logger.debug(f"[Keyword] Keywords Extracted: {unique_keywords}")
            return unique_keywords
        except Exception as e:
            logger.warning(f"[Warning] Keyword Extraction Failed: {e}")
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
        Multi-Query Hybrid Search: 여러 쿼리 관점으로 검색하여 재현율(recall) 극대화

        1. LLM으로 질문을 3가지 다른 검색 쿼리로 변환
        2. 각 쿼리로 독립적인 하이브리드 검색 (Dense + Sparse) 실행
        3. 결과를 (chapter_id, scene_index) 기준으로 병합, 최고 유사도 보존
        """
        top_k = kwargs.pop('top_k', settings.SEARCH_DEFAULT_TOP_K)

        # 짧은 질문 바이패스: 단순 질문은 multi-query 스킵하여 Gemini 호출 절약
        words = question.strip().split()
        if len(question) < 20 and len(words) <= 4:
            logger.info(f"[MultiQuery] Skipped (short question): '{question}'")
            keywords = self._extract_keywords(question)
            return self.find_similar_chunks(
                question=question,
                top_k=top_k,
                novel_id=novel_id,
                chapter_id=chapter_id,
                novel_filter=novel_filter,
                keywords=keywords,
                original_query=question,
                **kwargs
            )

        # 1. Multi-query 생성 (1회 LLM 호출)
        queries = self._generate_multi_queries(question)

        # 2. 각 쿼리로 검색 실행 및 결과 병합
        all_results: Dict[tuple, Dict] = {}

        for q in queries:
            keywords = self._extract_keywords(q)
            results = self.find_similar_chunks(
                question=q,
                top_k=top_k,
                novel_id=novel_id,
                chapter_id=chapter_id,
                novel_filter=novel_filter,
                keywords=keywords,
                original_query=question,  # 리랭커는 항상 원본 질문 사용
                **kwargs
            )

            for r in results:
                key = (r.get('chapter_id'), r.get('scene_index'))
                if key not in all_results or r['similarity'] > all_results[key]['similarity']:
                    all_results[key] = r

        # 3. 유사도 기준 정렬
        merged = sorted(all_results.values(), key=lambda x: x['similarity'], reverse=True)
        logger.info(f"[MultiQuery] 병합 결과: {len(merged)}건 (쿼리 {len(queries)}개 × top_k={top_k})")

        return merged[:top_k]

    def ask(
        self,
        question: str,
        alpha: float = DEFAULT_ALPHA,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        novel_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        novel_filter: Optional[str] = None,
        db=None
    ) -> Dict:
        """
        질문에 대한 답변 생성 (전체 파이프라인)

        검색 전략:
        1. 하이브리드 검색 (LLM 확장 + Dense + Sparse)
        2. 실패 시 원본 쿼리로 2차 검색 (폴백)

        Method C: db와 novel_id가 있으면 바이블 요약을 조회해 LLM에 주입.
        """
        # 1. 하이브리드 검색 실행
        logger.info(f"[Search] 원본 질문: '{question}'")
        top_chunks = self.hybrid_search(
            question=question,
            alpha=alpha,
            similarity_threshold=similarity_threshold,
            novel_id=novel_id,
            chapter_id=chapter_id,
            novel_filter=novel_filter
        )

        # 2. 결과 없으면 임계값을 낮춰 원본 쿼리로 재시도
        if not top_chunks:
            lowered_threshold = max(similarity_threshold - 0.1, 0.0)
            logger.warning(f"하이브리드 검색 결과 없음. 임계값 {similarity_threshold}→{lowered_threshold}으로 원본 쿼리 재시도")
            top_chunks = self.find_similar_chunks(
                question=question,
                top_k=settings.SEARCH_DEFAULT_TOP_K,
                alpha=alpha,
                similarity_threshold=lowered_threshold,
                novel_id=novel_id,
                chapter_id=chapter_id,
                novel_filter=novel_filter
            )

        # 3. 여전히 유사한 스토리보드가 없는 경우
        if not top_chunks:
            error_msg = "죄송합니다. 관련 내용을 찾을 수 없습니다."
            if not self.engine:
                error_msg += " (검색 엔진이 초기화되지 않았습니다)"
            elif self.engine and self.engine.index is None:
                error_msg += " (Pinecone 연결 실패 - BM25 폴백도 결과 없음)"
            
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
        
        # 4. LLM으로 답변 생성 (Method C: 바이블 주입)
        bible_summary = ""
        if db and novel_id:
            try:
                from backend.services.analysis_service import AnalysisService
                bible_summary = AnalysisService.get_bible_summary(db, novel_id, chapter_id)
            except Exception as e:
                logger.warning(f"바이블 요약 조회 실패 (novel={novel_id}): {e}")
        answer = self.generate_answer(question, context, bible=bible_summary)
        
        # 가장 높은 유사도 정보
        best_chunk = top_chunks[0]
        
        # novel title 가져오기 (캐시 사용)
        novel_title = self._get_novel_title(best_chunk['novel_id']) if best_chunk.get('novel_id') else "Unknown Novel"

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


# 싱글톤 인스턴스 (스레드 안전)
_chatbot_service = None
_chatbot_lock = threading.Lock()


def get_chatbot_service() -> ChatbotService:
    """
    챗봇 서비스 싱글톤 인스턴스 반환 (스레드 안전)

    Returns:
        ChatbotService: 챗봇 서비스 인스턴스
    """
    global _chatbot_service
    if _chatbot_service is None:
        with _chatbot_lock:
            if _chatbot_service is None:
                _chatbot_service = ChatbotService()
    return _chatbot_service

