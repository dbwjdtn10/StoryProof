import json
from google import genai
from backend.services.analysis import EmbeddingSearchEngine
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.core.prompts import STORY_GUARD_SYSTEM_PROMPT, STORY_PREDICTION_SYSTEM_PROMPT
from backend.core.config import settings

class StoryConsistencyAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.search_engine = EmbeddingSearchEngine()

    def check_consistency(self, novel_id: int, input_text: str):
        # 1. Pinecone 벡터 검색
        relevant_context = self.search_engine.search(input_text, novel_id, top_k=5)

        # 2. PostgreSQL 요약 정보 조회
        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            summary = novel.description if novel else "정보 없음"
        finally:
            db.close()

        # 3. Gemini 분석
        prompt = f"{STORY_GUARD_SYSTEM_PROMPT}\n\n[기존 설정]:\n{relevant_context}\n\n[요약]:\n{summary}\n\n[검토 문장]:\n{input_text}"
        
        try:
            # Replaced model.generate_content_async with client.models.generate_content (async not fully standard in simple client unless using async client, but let's assume standard usage or sync for stability if async is problematic, OR use the async client if available. 
            # Note: The original code used `await self.model.generate_content_async`.
            # The new SDK has `client.aio.models.generate_content`.
            
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except Exception as e:
            return {"status": "분석 오류", "message": str(e)}

    def predict_story(self, novel_id: int, user_input: str):
        # 1. Pinecone 벡터 검색 (관련 설정/장면 찾기)
        relevant_context = self.search_engine.search(user_input, novel_id, top_k=5)

        # 2. PostgreSQL 요약 정보 조회
        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            summary = novel.description if novel else "정보 없음"
        finally:
            db.close()

        # 3. Gemini 예측 생성
        prompt = f"{STORY_PREDICTION_SYSTEM_PROMPT}\n\n[기존 설정 및 장면]:\n{relevant_context}\n\n[소설 요약]:\n{summary}\n\n[사용자 가정(What-If)]: {user_input}"
        
        try:
            # Use synchronous call like ChatbotService
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            
            import re
            raw_text = response.text
            
            # Helper to try parsing JSON
            def try_parse_json(text):
                # 1. Try finding JSON object in text
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group())
                    except json.JSONDecodeError:
                        pass
                return None

            # 1. Attempt standard JSON parse
            parsed = try_parse_json(raw_text)
            
            if parsed:
                # Check for double-encoded JSON (AI sometimes returns json string inside json)
                if isinstance(parsed, dict) and 'prediction' in parsed:
                    val = parsed['prediction']
                    if isinstance(val, str) and val.strip().startswith('{'):
                         inner_parsed = try_parse_json(val)
                         if inner_parsed and 'prediction' in inner_parsed:
                             return inner_parsed
            
                return parsed

            # 2. Fallback: Regex extraction of the specific "prediction" value
            # Looks for "prediction": "..." or "prediction": '...'
            # This is risky with nested quotes but often works for simple failure cases
            pred_match = re.search(r'"prediction"\s*:\s*"(.*?)"(?=\s*\}|\s*,)', raw_text, re.DOTALL)
            if pred_match:
                # Need to manually unescape because we bypassed json.loads
                # Simple unescape for common chars
                content = pred_match.group(1)
                content = content.replace('\\"', '"').replace('\\n', '\n')
                return {"prediction": content}

            # 3. Final Fallback
            return {"prediction": raw_text.strip()}
                
        except Exception as e:
            print(f"Prediction Error: {e}")
            return {"prediction": f"예측 생성 중 오류가 발생했습니다: {str(e)}"}