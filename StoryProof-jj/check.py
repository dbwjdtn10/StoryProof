from fastapi import APIRouter, HTTPException
from pinecone import Pinecone
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
import os

router = APIRouter()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY", "your-pinecone-key"))
index = pc.Index("storyboard-index")
client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai"
)

class CheckRequest(BaseModel):
    current_text: str
    novel_id: int
    current_scene_index: Optional[int] = None

@router.post("/check-consistency")
async def check_consistency(request: CheckRequest):
    """
    [설정 오류 분석 로직 개선]
    - 원본과 수정한 텍스트를 비교하는 대신, 수정한 텍스트가 포함된 씬과 그 외의 전체 씬(요약문)들을 비교합니다.
    - 시스템 프롬프트에는 고정된 지침만 저장하고, 유저 프롬프트에 가변 데이터를 담아 캐싱 효율을 높입니다.
    """
    try:
        # 1. PostgreSQL/Pinecone에서 전체 씬의 요약문과 바이블 설정 조회
        # (실제 구현에서는 DB 조회가 필요하며, 여기서는 로직 구조를 보여줍니다)
        bible_data = "캐릭터 에이전트: 냉철하고 이성적인 마법사. 불을 다루는 마법을 극도로 꺼림."
        
        # 전체 씬 요약문 리스트 (예시 데이터)
        all_scenes = [
            {"index": 1, "summary": "주인공이 마법 탑에 입소한다."},
            {"index": 2, "summary": "스승으로부터 물의 마법 기초를 배운다."},
            {"index": 3, "summary": "도서관에서 금지된 마법 서적을 발견한다."}
        ]

        # 2. 스토리보드 구성 (수정된 씬 위치 표시)
        storyboard_str = ""
        for scene in all_scenes:
            prefix = "[현재 수정 중인 씬] " if scene["index"] == request.current_scene_index else ""
            storyboard_str += f"씬 {scene['index']}: {prefix}{scene['summary']}\n"

        # 3. LLM 통합 분석 (캐싱 최적화 구조)
        # 시스템 프롬프트: 고정된 가이드라인
        system_instruction = """너는 소설 전문 편집자이자 설정 검수 전문가야.
아래 제공되는 [설정 바이블]과 전체 [스토리보드]를 참고하여, [현재 작성 문장]에 설정 오류나 개연성 문제가 있는지 분석해줘.

분석 기준:
1. ⚠️ 설정 충돌: 바이블에 명시된 캐릭터 성격, 능력, 고유 설정 위반 여부
2. ⚙️ 개연성 경고: 이전 씬들의 흐름 및 캐릭터 상태와 모순되는 행동/상황
3. 🗣️ 보이스 불일치: 정해진 말투나 페르소나 이탈 여부

반드시 문제의 핵심을 짚어 간결하게 리포트 형식으로 응답해."""

        # 유저 프롬프트: 가변 데이터 (바이블, 스토리보드, 현재 문장)
        user_input = f"""
[설정 바이블]
{bible_data}

[스토리보드 (요약)]
{storyboard_str}

[현재 작성 문장]
{request.current_text}
"""

        report = client.chat.completions.create(
            model="gemini-1.5-flash", # 또는 "gemini-2.0-flash"
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            temperature=0.2
        )

        return {"report": report.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))