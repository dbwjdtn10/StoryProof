"""
설정 일관성 검사 및 스토리 예측 에이전트
StoryConsistencyAgent를 사용하여 소설의 설정 파괴를 탐지하고 스토리 전개를 예측합니다.
"""

import json
from google import genai
from backend.services.analysis import EmbeddingSearchEngine
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.core.config import settings


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

    def check_consistency(self, novel_id: int, input_text: str) -> dict:
        """
        설정 일관성 검사
        
        주어진 텍스트가 기존 소설 설정과 일관성이 있는지 검사합니다.
        Pinecone에서 관련 컨텍스트를 검색하고 Gemini API로 분석합니다.
        
        Args:
            novel_id (int): 소설 ID
            input_text (str): 검사할 텍스트
            
        Returns:
            dict: 분석 결과
                {
                    "status": "설정 파괴 감지" | "설정 일치",
                    "results": [
                        {
                            "type": "설정 충돌" | "개연성 경고",
                            "quote": "문제가 된 구절",
                            "description": "분석 내용",
                            "suggestion": "수정 제안"
                        }
                    ]
                }
        """
        # 1. Pinecone 벡터 검색으로 관련 컨텍스트 찾기
        search_results = self.search_engine.search(
            query=input_text, 
            novel_id=novel_id, 
            top_k=5
        )
        
        # 검색 결과를 텍스트로 변환
        relevant_context = self._format_search_results(search_results)

        # 2. PostgreSQL에서 소설 요약 정보 조회
        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            summary = novel.description if novel else "정보 없음"
        finally:
            db.close()

        # 3. Gemini API로 분석
        # prompts.py에서 가져온 프롬프트 사용
        from backend.core.prompts import STORY_GUARD_SYSTEM_PROMPT
        
        prompt = f"""{STORY_GUARD_SYSTEM_PROMPT}

[기존 설정]:
{relevant_context}

[요약]:
{summary}

[검토 문장]:
{input_text}"""
        
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={
                    'temperature': 0.1,
                    'response_mime_type': 'application/json'
                }
            )
            
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"[Error] 설정 일관성 검사 실패: {e}")
            return {
                "status": "분석 오류", 
                "message": str(e),
                "results": []
            }

    def predict_story(self, novel_id: int, user_input: str) -> dict:
        """
        스토리 전개 예측 (What-If 시나리오)
        
        사용자의 가정을 바탕으로 스토리가 어떻게 전개될지 예측합니다.
        
        Args:
            novel_id (int): 소설 ID
            user_input (str): 사용자의 가정 (예: "만약 주인공이 ~했다면?")
            
        Returns:
            dict: 예측 결과
                {
                    "prediction": "예측된 스토리 내용"
                }
        """
        # 1. Pinecone 벡터 검색 (관련 설정/장면 찾기)
        search_results = self.search_engine.search(
            query=user_input, 
            novel_id=novel_id, 
            top_k=5
        )
        
        relevant_context = self._format_search_results(search_results)

        # 2. PostgreSQL에서 소설 요약 정보 조회
        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            summary = novel.description if novel else "정보 없음"
        finally:
            db.close()

        # 3. Gemini API로 예측 생성
        from backend.core.prompts import STORY_PREDICTION_SYSTEM_PROMPT
        
        prompt = f"""{STORY_PREDICTION_SYSTEM_PROMPT}

[기존 설정 및 장면]:
{relevant_context}

[소설 요약]:
{summary}

[사용자 가정(What-If)]: {user_input}"""
        
        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_STRUCTURING_MODEL,
                contents=prompt,
                config={
                    'temperature': 0.3,  # 예측은 약간의 창의성 허용
                    'response_mime_type': 'application/json'
                }
            )
            
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            
            # JSON 파싱 시도, 실패하면 텍스트 그대로 반환
            try:
                return json.loads(clean_text)
            except json.JSONDecodeError:
                return {"prediction": clean_text}
                
        except Exception as e:
            print(f"[Error] 스토리 예측 실패: {e}")
            return {
                "prediction": f"예측 생성 중 오류가 발생했습니다: {str(e)}"
            }
    
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
            formatted.append(f"{text[:500]}...")  # 처음 500자만
            formatted.append("")
        
        return "\n".join(formatted)
