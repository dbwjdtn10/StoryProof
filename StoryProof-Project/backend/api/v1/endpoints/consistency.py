"""
소설 설정 및 개연성 검사 API 엔드포인트
- 기존 check.py의 기능을 프로젝트 구조에 맞춰 고도화
- Pinecone 기반 맥락 검색 및 DB 기반 바이블 설정 비교
"""

import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models import Analysis, AnalysisType, Chapter
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine

router = APIRouter()

class ConsistencyRequest(BaseModel):
    current_text: str
    novel_id: int
    current_scene_index: Optional[int] = None

class StoryValidator:
    def __init__(self, db: Session, engine: EmbeddingSearchEngine):
        self.db = db
        self.engine = engine
        self.client = OpenAI(
            api_key=settings.GOOGLE_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai"
        )

    def run_analysis(self, current_text: str, novel_id: int, current_index: int = None):
        """
        수정된 로직: 
        1. 요청받은 novel_id에 해당하는 Chapter만 엄격히 필터링
        2. 타 소설(예: 모밀꽃 필 무렵)이 섞이지 않도록 DB 쿼리 재점검
        """
        
        # [STEP 1] 특정 novel_id에만 속한 Chapter 조회 (타 파일 데이터 원천 차단)
        # 만약 novel_id가 파일 단위를 나타낸다면 아래 쿼리로 격리가 되어야 합니다.
        all_chapters = self.db.query(Chapter).filter(
            Chapter.novel_id == novel_id
        ).order_by(Chapter.chapter_number).all()

        storyboard_context = ""
        # 씬 요약 구성 시 파일명을 명시하지 않고 순수하게 '흐름'만 전달
        for i, c in enumerate(all_chapters):
            # 현재 분석 중인 씬과 나머지 씬을 명확히 구분
            is_current = (current_index is not None and i == current_index)
            status_tag = "[현재 수정 중인 장면]" if is_current else f"[이전 장면 {i+1}]"
            
            summary_text = c.content[:150] + "..." if c.content else "내용 없음"
            storyboard_context += f"{status_tag} 제목: {c.title}\n내용: {summary_text}\n\n"

        if not storyboard_context:
            storyboard_context = "이 소설 파일에 등록된 이전 회차가 없습니다."

        # [STEP 2] 바이블 조회 (해당 소설 전용)
        bible_record = self.db.query(Analysis).filter(
            Analysis.novel_id == novel_id,
            Analysis.analysis_type == AnalysisType.CHARACTER
        ).first()
        bible_settings = bible_record.result if bible_record else "등록된 바이블 설정이 없습니다."

        # [STEP 3] LLM 통합 분석
        return self.generate_llm_report(current_text, storyboard_context, bible_settings)

    def generate_llm_report(self, text, context, bible):
        system_prompt = (
            "당신은 소설의 내부 일관성을 검토하는 편집자입니다. "
            "당신의 분석 범위는 오직 '현재 제공된 텍스트'와 '해당 소설의 스토리보드'로 제한됩니다. "
            "다른 작품이나 외부 데이터와의 비교는 절대 하지 마십시오."
        )

        user_prompt = f"""
작가가 현재 소설의 특정 부분을 수정하거나 삭제했습니다. 
[기존 스토리보드]와 비교하여, [현재 수정본]에서 '내용 삭제'로 인해 앞뒤 인과관계가 끊긴 지점이 있는지 찾아내세요.

### [해당 소설의 설정 바이블]
{bible}

### [해당 소설의 기존 흐름 (스토리보드)]
{context}

### [현재 수정본]
{text}

---
### ⚠️ 주의사항:
1. **범위 제한**: [기존 스토리보드]에 있는 내용 중 [현재 수정본]에서 사라진 내용이 있다면, 그것이 뒷내용(개연성)에 문제를 일으키는지 분석하세요.
2. **타 작품 무시**: 이 소설과 관련 없는 다른 작품의 제목이 언급되더라도 무시하고, 오직 이 이야기 안에서의 논리만 보세요.
3. **삭제 감지**: 특히 씬 하나가 통째로 사라졌을 때, 그 씬에서 일어났던 '중요 사건'이 사라짐으로써 발생하는 논리적 공백을 짚어내야 합니다.

### 리포트 양식:
#### ### 소설 편집 리포트

**[현재 문장]:** "삭제된 씬의 영향으로 논리적 비약이 생긴 부분의 문장을 적으세요"

1. ⚠️ 설정 충돌: (설정과 모순되는 점)
2. ⚙️ 개연성 경고: (내용 삭제로 인해 앞뒤 연결이 어색해진 구체적인 이유)
3. 🗣️ 보이스 불일치: (해당 없음)

**[종합 의견]:** 삭제된 부분이 스토리 전체 흐름에 미치는 영향과 복구 필요성 제언.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=settings.GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2 # 분석의 정확도를 위해 낮춤
            )
            
            report_content = response.choices[0].message.content
            
            # 정규표현식 추출 (더 견고하게 보정)
            target_match = re.search(r'\[현재 문장\]:\*\*?\s*"([^"]*)"', report_content)
            target_sentence = target_match.group(1) if target_match else ""

            return {
                "report": report_content,
                "target_sentence": target_sentence,
                "status": "success"
            }
        except Exception as e:
            raise Exception(f"LLM 분석 중 오류 발생: {str(e)}")

# 전역 엔진 인스턴스 (최초 요청 시 로드)
_search_engine = None

def get_search_engine() -> EmbeddingSearchEngine:
    global _search_engine
    if _search_engine is None:
        try:
            _search_engine = EmbeddingSearchEngine()
        except Exception as e:
            print(f"❌ 검색 엔진 로드 실패: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="검색 엔진을 초기화할 수 없습니다."
            )
    return _search_engine

@router.post("/check")
async def check_consistency(
    request_data: ConsistencyRequest,
    db: Session = Depends(get_db),
    engine: EmbeddingSearchEngine = Depends(get_search_engine)
):
    try:
        validator = StoryValidator(db, engine)
        result = validator.run_analysis(
            request_data.current_text, 
            request_data.novel_id,
            request_data.current_scene_index
        )
        return result
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))