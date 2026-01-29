import os
import json
import sys
import io
import re
import PyPDF2
import olefile
import psycopg2
from dotenv import load_dotenv
from google import genai
from google.genai import types 
from sentence_transformers import SentenceTransformer

# [1] 시스템 인코딩 강제 설정 (터미널 출력 및 0xb8 에러 방지)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

load_dotenv()

class StoryBibleEngine:
    def __init__(self):
        # [중요] .env에서 값을 읽어오되, 없으면 기본값(None)을 넘겨 에러를 방지합니다.
        db_host = os.getenv("DB_HOST", "localhost")
        db_name = os.getenv("DB_NAME", "postgres")
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASS", "1234!@#$")

        if not all([db_name, db_user, db_pass]):
            print("❌ .env 설정 확인 필요: DB_NAME, DB_USER, DB_PASS 중 누락된 값이 있습니다.")

        # PostgreSQL 연결
        try:
            self.conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_pass,
                sslmode='disable'
            )
            print(f"[*] {db_name} 데이터베이스 연결 성공!")
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            sys.exit(1)
            
        self.create_table()
        
        self.embed_model = SentenceTransformer('BAAI/bge-m3')
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = "gemini-2.0-flash"
        
    def create_table(self):
        """저장 공간(테이블)을 자동으로 생성합니다."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS story_bible (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    metadata JSONB,
                    embedding DOUBLE PRECISION[]
                );
            """)
        self.conn.commit()

    def load_any_file(self, file_path):
        """[작가님 요청] 하나하나 인코딩을 확인하며 파일을 불러옵니다."""
        ext = os.path.splitext(file_path)[-1].lower()
        if ext == '.pdf': return self._load_pdf(file_path)
        if ext in ['.hwp', '.hwpx']: return self._load_hwp(file_path)

        # 텍스트 파일 인코딩 후보들
        encodings = ['cp949', 'utf-8', 'euc-kr', 'utf-16']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                    print(f"[*] '{enc}' 인코딩 확인 성공! 파일을 읽어옵니다.")
                    return content
            except Exception:
                continue
        
        # 마지막 수단: 바이너리로 읽고 강제 디코딩
        try:
            with open(file_path, 'rb') as f:
                return f.read().decode('cp949', errors='ignore')
        except:
            return ""

    def _load_pdf(self, file_path):
        text = ""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
        return text

    def _load_hwp(self, file_path):
        try:
            f = olefile.OleFileIO(file_path)
            return f.openstream('PrvText').read().decode('utf-16')
        except: return ""

    def save_to_postgresql(self, storyboard):
        """데이터를 PostgreSQL에 안전하게 저장합니다."""
        cuts = storyboard.get("cut_sequences", [])
        if not cuts:
            print("⚠️ 저장할 데이터가 없습니다.")
            return

        print(f"[*] 총 {len(cuts)}개의 장면을 저장 중...")
        
        # self.cur 대신 context manager(with)를 사용하여 안전하게 커서를 생성합니다.
        with self.conn.cursor() as cur:
            # 1. 기존 데이터 초기화 (선택 사항)
            cur.execute("DELETE FROM story_bible")
            
            for cut in cuts:
                # 데이터 추출
                content = str(cut)
                # 벡터 변환
                embedding = self.embed_model.encode(content).tolist()
                # 메타데이터 준비
                metadata = json.dumps(cut, ensure_ascii=False)
                
                # 2. 데이터 삽입 (테이블 이름: story_bible)
                cur.execute(
                    "INSERT INTO story_bible (content, metadata, embedding) VALUES (%s, %s, %s)",
                    (content, metadata, embedding)
                )
        
        # 3. 변경사항 저장
        self.conn.commit()
        print(f"[*] {len(cuts)}개 데이터 저장 완료!")

    def split_into_scenes_with_overlap(self, text, max_size=3000):
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        scenes, current_chunk, current_length = [], [], 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            if current_length + len(sentence) > max_size and current_chunk:
                scenes.append(" ".join(current_chunk))
                current_chunk, current_length = [], 0
            current_chunk.append(sentence)
            current_length += len(sentence)
        if current_chunk: scenes.append(" ".join(current_chunk))
        return scenes

    def _generate_structured_bible(self, text):
        prompt = f"다음 소설 장면을 분석해서 사건, 등장인물, 배경을 JSON 형식으로 요약해줘. 가급적 'scene_info'라는 키를 사용해줘:\n{text}"
        try:
            response = self.client.models.generate_content(
                model=self.model_name, 
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            data = json.loads(response.text)
            
            # [수정] 결과가 무엇이든 '리스트' 형태로 통일해서 내보냅니다.
            if isinstance(data, dict):
                content = data.get('scene_info') or data.get('cut_sequences') or data
                return [content] if isinstance(content, dict) else content
            return data if isinstance(data, list) else [data]    
        
        except Exception as e:
            print(f"      ⚠️ 제미나이 답변 해석 실패: {e}")
            return None

    def run(self, file_path):
        print(f"[*] 분석 시작: {file_path}")
        text = self.load_any_file(file_path)
        if not text: return
        
        scenes = self.split_into_scenes_with_overlap(text)
        storyboard = {"actor_sheets": {}, "cut_sequences": []}
        
        for i, scene_text in enumerate(scenes):
            data = self._generate_structured_bible(scene_text)
            if data:
                if isinstance(data, list):
                    storyboard["cut_sequences"].extend(data)
                else:
                    storyboard["cut_sequences"].append(data)
            print(f"  [>] {i+1}/{len(scenes)} 분석 중...")

        # 분석 후 바로 PostgreSQL 저장 함수 호출
        self.save_to_postgresql(storyboard)
        print("[*] 모든 작업이 성공적으로 끝났습니다!")


if __name__ == "__main__":
    try:
        engine = StoryBibleEngine()
        # 소설의 파일명을 여기에 적어주세요. (가능한 파일 .txt, .hwp, .hwpx, .pdf)
        engine.run("KR_fantasy_alice.txt")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")