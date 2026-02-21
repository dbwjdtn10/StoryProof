"""
설정 일관성 검사 및 스토리 예측 에이전트
StoryConsistencyAgent를 사용하여 소설의 설정 파괴를 탐지하고 스토리 전개를 예측합니다.
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from google import genai
from backend.services.analysis import EmbeddingSearchEngine
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.core.config import settings

logger = logging.getLogger(__name__)


class StoryConsistencyAgent:
    """
    설정 일관성 검사 및 스토리 예측 에이전트
    
    Attributes:
        client (genai.Client): Google Gemini API 클라이언트
        search_engine (EmbeddingSearchEngine): Pinecone 기반 벡터 검색 엔진
    """
    
    def __init__(self, api_key: str = None):
        """
        에이전트 초기화

        Args:
            api_key (str, optional): Google API 키. None이면 settings에서 가져옴
        """
        if not api_key:
            api_key = settings.GOOGLE_API_KEY

        self.client = genai.Client(api_key=api_key)

        # 이미 로드된 ChatbotService의 엔진을 재사용하여 중복 모델 로딩 방지
        try:
            from backend.services.chatbot_service import get_chatbot_service
            chatbot = get_chatbot_service()
            if chatbot.engine:
                self.search_engine = chatbot.engine
            else:
                self.search_engine = EmbeddingSearchEngine()
        except Exception:
            self.search_engine = EmbeddingSearchEngine()

    def _fetch_context_for_novel(self, novel_id: int, query: str, top_k: int = 7):
        """Pinecone 벡터 검색 + DB 소설 요약 조회를 단일 메서드로 통합.

        Returns:
            tuple: (relevant_context, summary, max_similarity)
        """
        search_results = self.search_engine.search(query=query, novel_id=novel_id, top_k=top_k)
        relevant_context = self._format_search_results(search_results)
        max_similarity = max((r.get('similarity', 0) for r in search_results), default=0)

        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            summary = novel.description if novel else "정보 없음"
        finally:
            db.close()

        return relevant_context, summary, max_similarity

    def _fetch_bible_summary(self, novel_id: int, chapter_id: int = None) -> str:
        """Analysis DB에서 바이블 요약 조회. 실패 시 빈 문자열 반환."""
        db = SessionLocal()
        try:
            from backend.services.analysis_service import AnalysisService
            return AnalysisService.get_bible_summary(db, novel_id, chapter_id)
        except Exception as e:
            logger.warning(f"바이블 요약 조회 실패 (novel={novel_id}): {e}")
            return ""
        finally:
            db.close()

    def _fetch_enriched_context(self, novel_id: int, query: str) -> tuple:
        """컨텍스트 + 바이블 병렬 조회 + 유사도 기반 gap detection 스킵.

        Returns:
            tuple: (relevant_context, summary, bible_block)
        """
        # 병렬: Pinecone 검색 + Bible 조회
        with ThreadPoolExecutor(max_workers=2) as executor:
            ctx_future = executor.submit(self._fetch_context_for_novel, novel_id, query)
            bible_future = executor.submit(self._fetch_bible_summary, novel_id)
            relevant_context, summary, max_similarity = ctx_future.result()
            bible = bible_future.result()

        if max_similarity < 0.7:
            for gap_q in self._identify_search_gaps(relevant_context, query):
                extra = self._format_search_results(
                    self.search_engine.search(query=gap_q, novel_id=novel_id, top_k=3)
                )
                if extra and extra != "관련 정보 없음":
                    relevant_context += f"\n\n[추가 검색]\n{extra}"
        else:
            logger.debug(f"Gap detection 스킵 (max_similarity={max_similarity:.3f} >= 0.7)")

        bible_block = f"\n\n[바이블 요약]:\n{bible}" if bible else ""
        return relevant_context, summary, bible_block

    def _parse_json_response(self, text: str, fallback_key: str = None) -> dict:
        """LLM JSON 응답 파싱. fallback_key 지정 시 파싱 실패 시 {fallback_key: text} 반환."""
        clean_text = text.replace('```json', '').replace('```', '').strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            if fallback_key:
                return {fallback_key: clean_text}
            raise

    def _identify_search_gaps(self, existing_context: str, query: str) -> list:
        """현재 검색 결과에서 누락된 정보를 파악, 추가 검색 쿼리 반환 (최대 2개)."""
        prompt = f"""아래 검색 결과가 질문에 답하기에 충분한지 평가하세요.

[질문]: {query}

[현재 검색 결과 (요약)]:
{existing_context[:600]}

부족한 정보가 있다면 추가 검색 키워드를 JSON 배열로 반환하세요 (최대 2개).
충분하면 빈 배열을 반환하세요.
반드시 JSON 배열만 반환: ["키워드1", "키워드2"] 또는 []"""
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={'temperature': 0.1, 'response_mime_type': 'application/json'}
            )
            result = json.loads(response.text.strip())
            return result[:2] if isinstance(result, list) else []
        except Exception:
            return []

    def check_consistency(self, novel_id: int, input_text: str, custom_prompt: str = None) -> dict:
        """
        설정 일관성 검사

        주어진 텍스트가 기존 소설 설정과 일관성이 있는지 검사합니다.
        Pinecone에서 관련 컨텍스트를 검색하고 Gemini API로 분석합니다.
        Agent-lite: 검색 공백 탐지 후 추가 검색 수행.
        Method C: Analysis DB 바이블 요약을 프롬프트에 직접 주입.
        """
        relevant_context, summary, bible_block = self._fetch_enriched_context(novel_id, input_text)

        custom_block = f"\n\n[작가 지시사항]:\n{custom_prompt}" if custom_prompt else ""

        from backend.core.prompts import STORY_GUARD_SYSTEM_PROMPT
        prompt = f"""{STORY_GUARD_SYSTEM_PROMPT}

[기존 설정]:
{relevant_context}{bible_block}{custom_block}

[요약]:
{summary}

[검토 문장]:
{input_text}"""

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={'temperature': 0.1, 'response_mime_type': 'application/json'}
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"설정 일관성 검사 실패: {e}")
            return {"status": "분석 오류", "message": str(e), "results": []}

    def predict_story(self, novel_id: int, user_input: str) -> dict:
        """
        스토리 전개 예측 (What-If 시나리오)

        사용자의 가정을 바탕으로 스토리가 어떻게 전개될지 예측합니다.
        gap detection 없이 컨텍스트+바이블 병렬 조회 후 LLM 1회 호출.
        """
        # 병렬: Pinecone 검색 + Bible 조회 (gap detection 불필요)
        with ThreadPoolExecutor(max_workers=2) as executor:
            ctx_future = executor.submit(self._fetch_context_for_novel, novel_id, user_input)
            bible_future = executor.submit(self._fetch_bible_summary, novel_id)
            relevant_context, summary, _ = ctx_future.result()
            bible = bible_future.result()

        bible_block = f"\n\n[바이블 요약]:\n{bible}" if bible else ""

        from backend.core.prompts import STORY_PREDICTION_SYSTEM_PROMPT
        prompt = f"""{STORY_PREDICTION_SYSTEM_PROMPT}

[기존 설정 및 장면]:
{relevant_context}{bible_block}

[소설 요약]:
{summary}

[사용자 가정(What-If)]: {user_input}"""

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={'temperature': 0.3, 'response_mime_type': 'application/json'}
            )
            return self._parse_json_response(response.text, fallback_key="prediction")
        except Exception as e:
            logger.error(f"스토리 예측 실패: {e}")
            return {"prediction": f"예측 생성 중 오류가 발생했습니다: {str(e)}"}
    
    def analyze_plot(self, novel_id: int, input_text: str, custom_prompt: str = None) -> dict:
        """
        플롯 구조 분석

        주어진 텍스트의 플롯 구조, 갈등, 전개 속도, 복선을 분석합니다.
        """
        relevant_context, summary, bible_block = self._fetch_enriched_context(novel_id, input_text[:500])

        custom_block = f"\n\n[작가 지시사항]:\n{custom_prompt}" if custom_prompt else ""

        from backend.core.prompts import PLOT_ANALYSIS_SYSTEM_PROMPT
        prompt = f"""{PLOT_ANALYSIS_SYSTEM_PROMPT}

[기존 설정]:
{relevant_context}{bible_block}{custom_block}

[요약]:
{summary}

[분석 대상 텍스트]:
{input_text}"""

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={'temperature': 0.1, 'response_mime_type': 'application/json'}
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"플롯 분석 실패: {e}")
            return {"error": str(e)}

    def analyze_style(self, novel_id: int, input_text: str, custom_prompt: str = None) -> dict:
        """
        문체 분석

        주어진 텍스트의 어조, 문장 구조, 어휘, 서술 시점을 분석합니다.
        """
        relevant_context, summary, bible_block = self._fetch_enriched_context(novel_id, input_text[:500])

        custom_block = f"\n\n[작가 지시사항]:\n{custom_prompt}" if custom_prompt else ""

        from backend.core.prompts import STYLE_ANALYSIS_SYSTEM_PROMPT
        prompt = f"""{STYLE_ANALYSIS_SYSTEM_PROMPT}

[기존 설정]:
{relevant_context}{bible_block}{custom_block}

[요약]:
{summary}

[분석 대상 텍스트]:
{input_text}"""

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={'temperature': 0.1, 'response_mime_type': 'application/json'}
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"문체 분석 실패: {e}")
            return {"error": str(e)}

    def _format_search_results(self, search_results: list) -> str:
        """
        검색 결과를 텍스트로 포맷팅
        
        Args:
            search_results (list): Pinecone 검색 결과
            
        Returns:
            str: 포맷팅된 텍스트
        """
        if not search_results:
            return "관련 정보 없음"
        
        formatted = []
        for i, result in enumerate(search_results, 1):
            doc = result.get('document', {})
            text = doc.get('original_text', '')
            summary = doc.get('summary', '')
            scene_idx = doc.get('scene_index', '?')
            
            formatted.append(f"[Scene {scene_idx}]")
            if summary:
                formatted.append(f"요약: {summary}")
            formatted.append(f"{text[:1000]}...")  # 처음 1000자
            formatted.append("")
        
        return "\n".join(formatted)


_agent_instance: "StoryConsistencyAgent | None" = None
_agent_lock = threading.Lock()


def get_consistency_agent() -> "StoryConsistencyAgent":
    """싱글톤 StoryConsistencyAgent 반환 (스레드 안전)."""
    global _agent_instance
    if _agent_instance is None:
        with _agent_lock:
            if _agent_instance is None:
                _agent_instance = StoryConsistencyAgent()
    return _agent_instance
