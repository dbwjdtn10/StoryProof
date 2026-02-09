from fastapi import APIRouter
from pinecone import Pinecone
from openai import OpenAI
import psycopg2

router = APIRouter()
pc = Pinecone(api_key="pcsk_5fsJcc_LVyYc2y1Y9Ab8bSXQvApZGNBV6PMh7H9iqWJ82WjbJTb9HPW3Pzr85AVCpf9xU2")
index = pc.Index("storyboard-index")
client = OpenAI(api_key="your-openai-api-key")

@router.post("/check-consistency")
async def check_consistency(current_text: str, novel_id: int):
    # 1. Pinecone에서 관련 스토리보드 맥락 검색 (Vector)
    # 이미지에서 선택한 multilingual-e5-large 모델 사용 가정
    search_res = index.query(
        vector=get_embedding(current_text), # 임베딩 함수
        top_k=3,
        include_metadata=True
    )
    story_context = [res.metadata['text'] for res in search_res.matches]

    # 2. PostgreSQL에서 바이블 설정 조회 (Structured)
    # 본문에서 이름 등을 추출하여 검색 (간단한 예시)
    bible_data = get_bible_from_db(novel_id) 

    # 3. LLM에게 3가지 포인트 검사 요청
    report = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content": f"""너는 소설 교정 전문가야. 
            아래 [바이블 설정]과 [과거 줄거리]를 참고해서 [현재 문장]의 오류를 찾아줘.
            
            분석 항목:
            1. ⚠️ 설정 충돌: 바이블의 외양/고유설정 위반
            2. ⚙️ 개연성 경고: 과거 줄거리의 상태(부상, 마나 등) 대비 어색한 행동
            3. 🗣️ 보이스 불일치: 캐릭터 페르소나와 말투 가이드 위반
            
            [바이블 설정]: {bible_data}
            [과거 줄거리]: {story_context}
            """},
            {"role": "user", "content": f"현재 작성 중인 문장: {current_text}"}
        ]
    )

    return {"report": report.choices[0].message.content}