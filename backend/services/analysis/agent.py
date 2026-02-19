import json
import re
from typing import Optional
from google import genai
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine
from backend.db.session import SessionLocal
from backend.db.models import Novel
from backend.core.prompts import STORY_GUARD_SYSTEM_PROMPT
from backend.core.config import settings

class StoryConsistencyAgent:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.search_engine = EmbeddingSearchEngine()

    async def check_consistency(self, novel_id: int, input_text: str, current_chapter_id: Optional[int] = None):
        # 1. Pinecone 벡터 검색
        # Exclude current chapter to prevent self-similarity from masking inconsistencies
        relevant_context_hits = self.search_engine.search(
            input_text, 
            novel_id=novel_id, 
            exclude_chapter_id=current_chapter_id,
            top_k=15
        )
        
        # Format context for the prompt
        context_str = ""
        for i, hit in enumerate(relevant_context_hits):
            doc = hit['document']
            context_str += f"[관련 씬 {i+1}]\n제목/요약: {doc.get('summary', '없음')}\n내용: {doc.get('original_text', '')}\n\n"

        # 2. 소설 전체 요약 정보 조회
        db = SessionLocal()
        try:
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            novel_description = novel.description if novel else "정보 없음"
        finally:
            db.close()

        # 3. Gemini 분석
        prompt = f"""{STORY_GUARD_SYSTEM_PROMPT}

[기존 설정 데이터]:
{context_str if context_str else "설정 데이터 없음 (새로운 설정으로 간주될 수 있음)"}

[전체 줄거리 요약]:
{novel_description}

[검토 문장 (현재 집필 중인 내용)]:
{input_text}

주의: '죽음'이나 '심각한 부상', '갑작스러운 성격 변화' 등은 매우 중대한 '개연성 및 설정' 요소입니다.
만약 [기존 설정 데이터]나 [전체 줄거리 요약]에 그러한 암시가 전혀 없는데 갑자기 발생했다면, 반드시 '개연성 경고'를 발생시키세요.
"""
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use aio for async generation
                # Enable JSON mode for more reliable parsing
                response = await self.client.aio.models.generate_content(
                    model=settings.GEMINI_CHAT_MODEL,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json"
                    }
                )
                
                raw_text = response.text.strip()
                
                # Extract JSON more robustly
                json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
                clean_text = json_match.group(1) if json_match else raw_text
                
                # Simple cleanup for common issues
                clean_text = clean_text.replace('```json', '').replace('```', '').strip()
                
                try:
                    return json.loads(clean_text)
                except json.JSONDecodeError as je:
                    # If first attempt fails, try basic escaping fix for quotes within quotes
                    print(f"[Warning] JSON Decode Error, attempting recovery: {je}")
                    return json.loads(clean_text)
                    
            except Exception as e:
                wait_time = (2 ** attempt) + 1
                if "429" in str(e):
                    wait_time += 5 # Additional wait for rate limits
                    print(f"[Warning] Rate limit hit (429), waiting {wait_time}s before retry {attempt+1}/{max_retries}...")
                else:
                    print(f"[Error] StoryConsistencyAgent Analysis Error (Attempt {attempt+1}): {e}")
                
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    return {"status": "분석 오류", "message": f"API 호출 실패 ({max_retries}회 시도): {str(e)}"}
