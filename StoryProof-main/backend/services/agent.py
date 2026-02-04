import json
from google import genai
from backend.services.analysis import EmbeddingSearchEngine
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.core.prompts import STORY_GUARD_SYSTEM_PROMPT
from backend.core.config import settings

class StoryConsistencyAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.search_engine = EmbeddingSearchEngine()

    async def check_consistency(self, novel_id: int, input_text: str):
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
            
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except Exception as e:
            return {"status": "분석 오류", "message": str(e)}