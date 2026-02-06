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

    async def check_consistency(self, novel_id: int, input_text: str, current_scene_index: int = None):
        db = SessionLocal()
        try:
            # 1. 고정 설정 (바이블/소설 기본 정보) 조회
            novel = db.query(Novel).filter(Novel.id == novel_id).first()
            bible_data = novel.description if novel else "설정된 바이블 정보가 없습니다."

            # 2. 전체 흐름 (스토리보드) 조회
            # 모든 씬의 요약을 가져와 전체적인 맥락을 파악합니다.
            from backend.db.models import Scene
            scenes = db.query(Scene).filter(Scene.novel_id == novel_id).order_by(Scene.index).all()
            storyboard_str = ""
            for s in scenes:
                prefix = "[현재 수정 중인 씬] " if s.index == current_scene_index else ""
                storyboard_str += f"씬 {s.index}: {prefix}{s.summary}\n"

            # 3. 구체적 관련 설정 (벡터 검색)
            # 현재 문장과 가장 밀접한 설정을 검색합니다.
            relevant_context = self.search_engine.search(input_text, novel_id, top_k=5)

            # 4. Gemini 통합 분석
            system_instruction = """당신은 소설 전문 편집자이자 설정 검수 전문가입니다.
제공된 [설정 바이블], [전체 스토리보드], [관련 세부 설정]을 바탕으로 [검토 문장]을 분석하세요.

분석 기준:
1. ⚠️ 설정 충돌: 바이블 및 기존 설정 데이터와 캐릭터 성격, 능력, 역사 등이 충돌하는지 확인.
2. ⚙️ 개연성 경고: 전체 스토리보드의 흐름상 앞뒤가 맞지 않거나 갑작스러운 전개가 있는지 확인.
3. 🗣️ 보이스 불일치: 캐릭터의 말투나 페르소나가 기존과 달라졌는지 확인.

반드시 JSON 형식으로만 응답해야 하며, 아주 사소한 위화감도 놓치지 마세요."""

            user_prompt = f"""
[설정 바이블]
{bible_data}

[전체 스토리보드 (요약)]
{storyboard_str}

[관련 세부 설정 (검색 결과)]
{relevant_context}

[검토 문장]
{input_text}

답변 형식:
{{
    "status": "설정 파괴 감지" 또는 "설정 일치",
    "violation_point": "문제가 된 구절",
    "reason": "구체적인 충돌 또는 어색함의 이유 (번호를 매겨 상세히)",
    "suggestion": "자연스러운 수정을 위한 구체적인 대안 제시"
}}
"""
            
            response = await self.client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json"
                }
            )
            
            # response_mime_type: "application/json"을 사용하므로 바로 json.loads 가능
            return json.loads(response.text)
        except Exception as e:
            return {"status": "분석 오류", "message": str(e)}
        finally:
            db.close()