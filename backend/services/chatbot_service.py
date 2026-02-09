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
    DEFAULT_SIMILARITY_THRESHOLD = 0.5  # 유사도 임계값 (할루시네이션 방지를 위해 상향)

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
        novel_id: Optional[int] = None,
        chapter_id: Optional[int] = None,
        novel_filter: Optional[str] = None
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
                    print(f"🔎 Chatbot: Resolved novel_filter '{novel_filter}' to ID {novel_id} ({novel.title})")
                else:
                    print(f"⚠️ Chatbot: novel_filter '{novel_filter}' not found in DB")
            finally:
                db.close()
        elif novel_id:
            print(f"🔎 Chatbot: Using direct novel_id {novel_id}")
        
        # Step 2: Pinecone 벡터 검색 실행
        try:
            results = self.engine.search(query=question, novel_id=novel_id, chapter_id=chapter_id, top_k=top_k)
            print(f"🔍 Chatbot: Found {len(results)} results (Novel: {novel_id}, Chapter Context: {chapter_id})")
            
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

[중요 규칙 - 할루시네이션 방지]
1. **반드시 제공된 문맥에 있는 정보만 사용하세요.**
2. **문맥에 없는 내용은 절대 추측하거나 외부 지식을 사용하지 마세요.**
3. **답변할 수 없는 경우 "제공된 문맥에서 해당 정보를 찾을 수 없습니다"라고 명시하세요.**
4. **각 주장에는 어느 Context에서 가져왔는지 [Context N] 형태로 출처를 표시하세요.**

[답변 형식]
반드시 다음 형식을 지켜주세요. 두 섹션 사이에는 빈 줄을 두세요.

[핵심 요약]
(질문에 대한 핵심 답변을 1~2문장으로 요약하고, 출처를 표시) [Context N]

[상세 설명]
(문맥을 바탕으로 한 구체적인 설명과 근거. 각 문장마다 출처 표시) [Context N]

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
    
    def augment_query(self, question: str) -> str:
        """
        사용자 질문을 검색에 최적화된 형태로 확장합니다.
        Gemini를 사용하여 관련 키워드, 동의어, 구체적인 표현을 추가합니다.
        
        중요: 원본 질문을 반드시 유지하고, 추가 키워드만 덧붙입니다.
        """
        if not self.client:
            return question

        prompt = f"""당신은 소설 검색 전문가입니다. 사용자의 질문을 분석하여 검색에 최적화된 쿼리로 확장하세요.

사용자 질문: "{question}"

[중요 원칙]
1. **원본 질문을 절대 축약하거나 변경하지 마세요**
2. **원본 질문 뒤에 관련 키워드만 추가하세요**
3. **질문의 의미를 정확히 보존하세요**

[시간적 순서 키워드 인식]
- "처음", "첫", "최초" → 초반 씬, 등장, 시작, 첫 번째, Scene 1-5, 첫 만남, 첫 등장
- "마지막", "최후", "끝" → 후반 씬, 종료, 마무리, 마지막 Scene, 최후, 종결
- "가장", "제일", "최고" → 강조, 극단, 최상급, 가장 중요한
- "유일한", "단 하나" → 독특, 특별, 오직, 유일

[확장 규칙]
1. **원본 질문 전체를 그대로 유지**
2. **시간 키워드가 있으면 관련 표현 추가** (예: "처음" → "첫 번째, 최초, 초반, 시작")
3. **핵심 엔티티(인물명, 장소명) 유지**
4. **동의어 및 관련 표현 추가**
5. **씬 위치 힌트 추가** (시간 조건이 있는 경우)

[출력 형식]
원본 질문 + 추가 키워드 (한 줄, 설명 없이, 따옴표 없이)

[예시]
입력: "앨리스가 처음 만난 인물"
출력: 앨리스가 처음 만난 인물 첫 번째 최초 등장 초반 시작 Scene 1 Scene 2 Scene 3 첫 등장인물 첫 만남

입력: "도로시가 처음만난 인물이 누구양?"
출력: 도로시가 처음만난 인물이 누구양 도로시 처음 만난 인물 첫 번째 최초 등장 초반 시작 Scene 1 Scene 2 Scene 3 첫 등장인물 첫 만남

입력: "앨리스가 떨어진 곳"
출력: 앨리스가 떨어진 곳 장소 위치 토끼굴 구멍 낙하 떨어짐

입력: "토끼가 마지막으로 한 말"
출력: 토끼가 마지막으로 한 말 최후 종료 끝 후반 마무리 마지막 대사 마지막 Scene

입력: "가장 중요한 사건"
출력: 가장 중요한 사건 최고 핵심 주요 결정적 중대한 전환점 클라이맥스

출력:"""
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_CHAT_MODEL,
                contents=prompt,
                config={
                    'temperature': 0.2,  # 낮은 temperature로 일관성 유지
                    'max_output_tokens': 200  # 충분한 키워드 생성
                }
            )
            augmented = response.text.strip()
            
            # 따옴표 제거 (Gemini가 가끔 따옴표로 감싸는 경우 대비)
            augmented = augmented.strip('"').strip("'")
            
            print(f"🧬 Query Augmented: '{question}' -> '{augmented}'")
            return augmented
        except Exception as e:
            print(f"⚠️ Query Augmentation Failed: {e}")
            return question

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
        1. [개선] 항상 쿼리 확장 적용 (LLM으로 키워드 추가)
        2. 확장된 쿼리로 1차 검색
        3. 실패 시 원본 쿼리로 2차 검색 (폴백)
        
        예상 효과: 유사도 +8~15% 향상
        """
        # 1. [개선] 항상 쿼리 확장 적용
        print(f"🔍 원본 질문: '{question}'")
        augmented_query = self.augment_query(question)
        
        # 확장이 실제로 일어났는지 확인
        if augmented_query != question:
            print(f"✨ 확장된 질문: '{augmented_query}'")
            search_query = augmented_query
        else:
            print("ℹ️ 쿼리 확장 실패 또는 불필요, 원본 사용")
            search_query = question
        
        # 2. 확장된 쿼리로 1차 검색
        top_chunks = self.find_similar_chunks(
            question=search_query,
            top_k=5,
            alpha=alpha,
            similarity_threshold=similarity_threshold,
            novel_id=novel_id,
            chapter_id=chapter_id,
            novel_filter=novel_filter
        )
        
        # 3. 실패 시 원본 쿼리로 2차 검색 (폴백)
        if not top_chunks and search_query != question:
            print("⚠️ 확장 쿼리 검색 실패, 원본 쿼리로 재시도...")
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

