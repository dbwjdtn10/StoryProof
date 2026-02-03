import os
import re
import google.generativeai as genai  # Google 공식 라이브러리 사용
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# .env 파일을 읽어와서 환경변수로 등록
load_dotenv()

from backend.core.config import settings
from backend.db.session import get_db
from backend.db.models import Analysis, AnalysisType, VectorDocument
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine

router = APIRouter()

class ConsistencyRequest(BaseModel):
    current_text: str
    novel_id: int
    current_scene_index: Optional[int] = None

class StoryValidator:
    def __init__(self, db, engine):
        self.db = db
        self.engine = engine  # EmbeddingSearchEngine 인스턴스
        
        # .env의 GOOGLE_API_KEY 사용
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("API 키(GOOGLE_API_KEY)가 .env 파일에 설정되지 않았습니다.")

        # Google Gemini 설정
        genai.configure(api_key=api_key)
        
        # 모델명 설정 (오타 방지 로직 포함)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if "2.5" in model_name: 
            model_name = "gemini-2.5-flash"
            
        self.model = genai.GenerativeModel(model_name)

    def run_analysis(self, current_text: str, novel_id: int, current_scene_index: Optional[int] = None):
        """
        [설정 오류 분석 로직]
        1. Pinecone 검색을 통한 유사 맥락 추출
        2. DB의 모든 씬 요약본 로드
        3. 바이블 설정 로드
        4. Gemini 통합 분석
        """
        
        # STEP 1: Pinecone 맥락 검색 (함수명을 search로 수정)
        try:
            # embedding_engine.py의 search(query, novel_id, top_k) 호출
            search_hits = self.engine.search(query=current_text, novel_id=novel_id, top_k=3)
            
            # 검색된 결과에서 요약문만 추출하여 문자열화
            context_str = ""
            for hit in search_hits:
                summary = hit['document'].get('summary', '요약 없음')
                context_str += f"- 관련 맥락: {summary}\n"
            print(f"✅ Pinecone 검색 완료. {len(search_hits)}개의 유사 맥락 추출됨.")
        except Exception as e:
            print(f"❌ Pinecone 검색 실패: {e}")
            context_str = "참고할 과거 맥락이 없습니다."

        # STEP 2: DB에서 전체 스토리보드(씬 요약) 가져오기
        all_docs = self.db.query(VectorDocument).filter(
            VectorDocument.novel_id == novel_id
        ).order_by(VectorDocument.chunk_index).all()
        
        storyboard_str = ""
        if not all_docs:
            storyboard_str = "기록된 스토리보드가 없습니다."
        else:
            for doc in all_docs:
                scene_data = doc.metadata_json
                idx = doc.chunk_index
                summary = scene_data.get('summary', '요약 없음')
                prefix = "[현재 수정 중인 위치] " if idx == current_scene_index else ""
                storyboard_str += f"씬 {idx}: {prefix}{summary}\n"

        # STEP 3: PostgreSQL 바이블 조회
        bible_record = self.db.query(Analysis).filter(
            Analysis.novel_id == novel_id,
            Analysis.analysis_type == AnalysisType.CHARACTER
        ).first()
        
        bible_settings = bible_record.result if bible_record else "등록된 캐릭터 설정이 없습니다."

        # STEP 4: Gemini 통합 분석 리포트 생성
        print(f"🚀 Gemini 분석 리포트 생성 시작... (novel_id: {novel_id})")
        return self.generate_llm_report(current_text, storyboard_str, context_str, bible_settings)

    def generate_llm_report(self, text, storyboard, context, bible):
        prompt = f"""너는 소설 전문 편집자이자 설정 검수 전문가야.
작가가 작성한 [전체 텍스트]를 분석하여 [설정 바이블] 및 [전체 흐름]과 충돌하거나 어색한 부분이 있다면 지적해줘.

[설정 바이블]:
{bible}

[전체 스토리보드]:
{storyboard}

[검색된 유사 맥락]:
{context}

[전체 텍스트]:
{text}

### 분석 미션:
1. [전체 텍스트] 중에서 **오류나 모순이 있는 구체적인 문장**을 하나 이상 찾아내라.
2. 찾아낸 문장을 **[현재 문장]** 항목에 정확히 복사해서 넣어라. 만약 여러 문장이 문제라면 가장 핵심적인 문장 하나를 선택하거나 합쳐서 적어라.
3. 해당 문장이 왜 문제인지 분석 기준에 맞춰 설명해라.
4. 만약 특별한 문제가 없다면, [현재 문장]에는 전체 텍스트의 첫 문장을 적고 리포트 항목에 "특이 사항 없음"이라고 적어라.

### 리포트 양식:
#### ### 소설 편집 리포트
**[현재 문장]:** "문제되는 문장을 여기에 복사"

1. ⚠️ 설정 충돌: (내용)

2. ⚙️ 개연성 경고: (내용)

3. 🗣️ 보이스 불일치: (내용)

**[종합 의견]:** 해결책 제시.
"""
        
        try:
            response = self.model.generate_content(prompt)
            report_content = response.text
            
            # [현재 문장] 추출용 정규식 (유연하게 매칭)
            target_match = re.search(r'\*\*\[현재 문장\]:\*\* "(.*?)"', report_content)
            if not target_match:
                target_match = re.search(r'\[현재 문장\]: (.*)', report_content)
                
            target_sentence = target_match.group(1).strip() if target_match else ""
            
            # 따옴표 제거
            target_sentence = target_sentence.strip('"').strip("'")

            return {
                "report": report_content,
                "target_sentence": target_sentence,
                "status": "success"
            }
        except Exception as e:
            print(f"❌ Gemini 분석 실패: {e}")
            return {"report": f"분석 중 오류 발생: {str(e)}", "status": "error"}

# 전역 엔진 인스턴스 관리
_search_engine = None

def get_search_engine() -> EmbeddingSearchEngine:
    global _search_engine
    if _search_engine is None:
        try:
            _search_engine = EmbeddingSearchEngine()
        except Exception as e:
            print(f"❌ 검색 엔진 로드 실패: {e}")
            raise HTTPException(status_code=503, detail="검색 엔진 초기화 실패")
    else:
        print("✅ 검색 엔진이 이미 로드되어 있습니다. 기존 엔진을 사용합니다.")
    return _search_engine

@router.post("/check")
async def check_consistency(
    request_data: ConsistencyRequest,
    db: Session = Depends(get_db),
    engine: EmbeddingSearchEngine = Depends(get_search_engine)
):
    try:
        print(f"🔍 Consistency check 요청 수신: novel_id={request_data.novel_id}")
        validator = StoryValidator(db, engine)
        result = validator.run_analysis(
            request_data.current_text, 
            request_data.novel_id,
            request_data.current_scene_index
        )
        print("✅ Consistency check 완료 및 응답 전송")
        return result
    except Exception as e:
        print(f"❌ Consistency check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))