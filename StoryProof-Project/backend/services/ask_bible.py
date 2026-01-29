import os
import re
import psycopg2
import numpy as np
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer

load_dotenv()

class StoryBibleQA:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.embed_model = SentenceTransformer('BAAI/bge-m3')
        
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            sslmode='disable'
        )
        self.cur = self.conn.cursor()
        print("[*] PostgreSQL(VectorDB) 연결 성공!")
        
    def ask(self, query):
        # 1. 챕터 필터링
        chapter_match = re.search(r'(\d+)장', query)
        
        # 2. VectorDB 검색
        query_emb = self.embed_model.encode(query)
        
        try:
            if chapter_match:
                chapter_val = chapter_match.group(1)
                self.cur.execute("SELECT content, embedding FROM story_bible WHERE metadata->>'chapter' = %s", (chapter_val,))
            else:
                self.cur.execute("SELECT content, embedding FROM story_bible")
            
            rows = self.cur.fetchall()
            if not rows:
                print("⚠️ 검색된 데이터가 없습니다.")
                return
            
            results = []
            for content, emb in rows:
                # DB에 저장된 벡터(문자열/리스트 형태)를 넘파이 배열로 변환
                db_emb = np.array(emb)
                # 코사인 유사도 계산
                score = np.dot(query_emb, db_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(db_emb))
                results.append((content, score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            top_results = results[:10]
            context = "\n".join([r[0] for r in top_results])
            
        except Exception as e:
            print(f"❌ 검색 중 오류 발생: {e}")
            return
        
        # 3. Gemini 최종 답변 (질문의 디테일을 살리기 위해 페르소나 강화)
        prompt = f"""당신은 소설 '이상한 나라의 앨리스'의 모든 장면을 꿰뚫고 있는 전문 편집자입니다.
        작가님의 질문에 대해 다음 지침을 지켜 답변하세요:

        - '스토리보드', '데이터', '컷 번호', '필드' 같은 기술적인 용어나 시스템 명칭을 절대 언급하지 마세요.
        - 대신 "앨리스가 ~하는 장면을 떠올려보면", "~라고 말하던 대목에서 알 수 있듯이"와 같이 장면의 구체적인 상황을 묘사하며 답변을 시작하세요.
        - 근거가 되는 구체적인 행동이나 대사를 문장 안에 자연스럽게 녹여내어, 작가님이 따로 데이터를 찾아보지 않아도 어느 장면인지 알 수 있게 하세요.
        - 어떤 소제목, 번호, 머리말도 사용하지 말고 오직 매끄러운 줄글로만 답변하세요.

        [분석된 장면 정보]:
        {context}
        
        질문: {query}"""
        
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        print(f"\n💡 답변: {response.text}")

if __name__ == "__main__":
    qa = StoryBibleQA()

    print("[*] 시스템이 준비되었습니다.")
    # 테스트 질문들을 여기에 적어주세요. qs.ask("이 안에 질문을 적어주세요.")
    qa.ask("앨리스가 ‘고양이’ 이야기를 꺼냈을 때 상대가 화를 낸 이유는 무엇이었나?")
    qa.ask("코커스 경주에서 도도새는 승자를 어떻게 정했나?")
    qa.ask("코커스 경주가 끝난 뒤 앨리스가 나눠 준 상은 무엇이었나?")
    qa.ask("앨리스가 버섯을 먹어 키를 조절하려 한 목적은 무엇이었나?")
    qa.ask("앨리스가 “난 누구지?”라고 혼란스러워한 계기는 무엇이었나?")
    qa.ask("앨리스가 자신을 확인하려고 시도한 방법을 한 가지 말해줄래?")
    qa.ask("생쥐의 ‘이야기’가 오해를 부른 말장난은 무엇이었나?")
    qa.ask("앨리스가 “고양이가 박쥐를 먹을까?” 같은 말을 반복하게 된 상태는 무엇이었나?")