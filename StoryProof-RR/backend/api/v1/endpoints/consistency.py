"""
소설 설정 및 개연성 검사 API 엔드포인트
- 기존 check.py의 기능을 프로젝트 구조에 맞춰 고도화
- Pinecone 기반 맥락 검색 및 DB 기반 바이블 설정 비교
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models import Analysis, AnalysisType
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine

router = APIRouter()

class ConsistencyRequest(BaseModel):
    current_text: str
    novel_id: int

class StoryValidator:
    def __init__(self, db: Session, engine: EmbeddingSearchEngine):
        self.db = db
        self.engine = engine
        self.client = OpenAI(
            api_key=settings.GOOGLE_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai"
        )

    def run_analysis(self, current_text: str, novel_id: int):
        """
        '설정파괴분석기' 메인 분석 프로세스
        """
        # STEP 1: Pinecone 맥락 검색 (스토리보드)
        search_res = self.engine.search(query=current_text, novel_id=novel_id, top_k=5)
        storyboard_context = [res['document'].get('summary', '') for res in search_res]
        
        if not storyboard_context:
            storyboard_context = ["과거 기록이 없습니다."]

        # STEP 2: PostgreSQL 바이블 조회 (JSONB)
        bible_record = self.db.query(Analysis).filter(
            Analysis.novel_id == novel_id,
            Analysis.analysis_type == AnalysisType.CHARACTER
        ).first()
        
        bible_settings = bible_record.result if bible_record else "등록된 바이블/캐릭터 설정이 없습니다."

        # STEP 3: LLM 통합 분석 및 리포트 생성
        return self.generate_llm_report(current_text, storyboard_context, bible_settings)

    def generate_llm_report(self, text, context, bible):
        prompt = f"""
당신은 소설 전문 편집자입니다. 작가가 쓴 [최근 작성 내용]이 [바이블] 및 [과거 줄거리]와 충돌하는지 핵심만 분석하세요.

[최근 작성 내용]:
{text}

[설정 바이블]:
{bible}

[과거 줄거리]:
{context}

---

### 지침:
1. **가장 심각한 오류 하나**만 골라서 아주 간결하게 리포트하세요. 
2. **반드시** 문제가 된 구체적인 문장을 [현재 문장] 항목에 적어주세요. 
3. 전체 분량은 10~15줄 내외로 짧게 유지하세요.

### 리포트 양식:
#### ### 소설 편집 리포트

**[현재 문장]:** "오류가 발견된 실제 문장을 여기에 따옴표로 적으세요"

1. ⚠️ 설정 충돌: (간결하게 한 줄)
2. ⚙️ 개연성 경고: (간결하게 한 줄)
3. 🗣️ 보이스 불일치: (간결하게 한 줄)

**[종합 의견]:** 한두 문장으로 해결책 제시.
"""
        
        response = self.client.chat.completions.create(
            model=settings.GEMINI_MODEL,
            messages=[
                {"role": "system", "content": "너는 핵심만 짚어주는 유능한 소설 편집자이다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        report_content = response.choices[0].message.content
        
        # [현재 문장]: 뒤의 텍스트를 추출하여 target_sentence로 활용 (프론트엔드 네비게이션용)
        import re
        target_match = re.search(r'\*\*\[현재 문장\]:\*\* "(.*?)"', report_content)
        target_sentence = target_match.group(1) if target_match else ""

        return {
            "report": report_content,
            "target_sentence": target_sentence,
            "metadata": {
                "context_count": len(context) if isinstance(context, list) else 0,
                "has_bible": bible != "등록된 바이블/캐릭터 설정이 없습니다."
            }
        }

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
    """
    현재 작성 중인 문장과 소설의 기존 설정(바이블) 및 과거 줄거리 간의 일관성을 검사합니다.
    """
    try:
        validator = StoryValidator(db, engine)
        result = validator.run_analysis(request_data.current_text, request_data.novel_id)
        return result

    except Exception as e:
        print(f"❌ Consistency check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"일관성 검사 중 오류가 발생했습니다: {str(e)}"
        )
