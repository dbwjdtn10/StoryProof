"""
소설 코퍼스 DB/Pinecone 업로드 스크립트
=======================================
novel_corpus_kr 폴더의 소설 텍스트 파일들을 읽어
DB(PostgreSQL)와 벡터 DB(Pinecone)에 업로드합니다.

평가 스크립트(evaluate_*.py)를 실행하기 전 필수 선행 작업입니다.

기능:
1. novel_corpus_kr/*.txt 파일 스캔
2. 임시 사용자(tester) 및 소설/챕터 생성
3. 텍스트를 씬 단위로 분할 (SceneChunker 사용)
4. EmbeddingSearchEngine을 통해 벡터화 및 저장

사용법:
    python scripts/upload_corpus_to_db.py
"""

import os
import sys
import glob
from tqdm import tqdm

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.db.models import User, Novel, Chapter
from backend.core.config import settings
from backend.services.analysis.scene_chunker import SceneChunker
from backend.services.analysis.embedding_engine import EmbeddingSearchEngine

# 설정
CORPUS_DIR = "novel_corpus_kr"
TEST_USER_EMAIL = "corpus_tester@example.com"
TEST_USER_PASSWORD = "password123"


def get_or_create_user(db):
    """테스트용 사용자 생성"""
    user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
    if not user:
        print(f"👤 테스트 유저 생성: {TEST_USER_EMAIL}")
        user = User(
            email=TEST_USER_EMAIL,
            username="corpus_tester", # username 추가
            hashed_password=TEST_USER_PASSWORD, # 해싱 생략 (테스트용)
            is_active=True,
            user_mode="writer" # user_mode로 변경된 컬럼
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def process_novel(db, filepath: str, user_id: int):
    """소설 파일 처리"""
    filename = os.path.basename(filepath)
    title = filename.replace("KR_", "").replace(".txt", "").replace("_", " ").title()
    
    # 한국어 제목 매핑 (파일명 -> 제목)
    TITLE_MAP = {
        "fantasy_alice": "이상한 나라의 앨리스",
        "romance_jane": "제인 에어",
        "mystery_sherlock": "셜록 홈즈",
        "sf_frankenstein": "프랑켄슈타인",
        "horror_jekyll": "지킬 박사와 하이드",
    }
    
    # 파일명 핵심 키워드로 매핑 확인
    key = filename.replace("KR_", "").replace(".txt", "")
    if key in TITLE_MAP:
        title = TITLE_MAP[key]
    
    print(f"\n📚 소설 처리 중: {title} ({filename})")
    
    # 1. 소설 생성/조회
    novel = db.query(Novel).filter(Novel.title == title, Novel.author_id == user_id).first()
    if not novel:
        novel = Novel(
            title=title,
            description=f"평가용 코퍼스 자동 업로드 ({filename})",
            author_id=user_id,
            genre=key.split('_')[0] if '_' in key else "General"
        )
        db.add(novel)
        db.commit()
        db.refresh(novel)
        print(f"  ✅ 소설 생성 완료 (ID: {novel.id})")
    else:
        print(f"  ℹ️ 이미 존재하는 소설 (ID: {novel.id})")
    
    # 2. 챕터 생성 (단일 챕터로 처리)
    chapter_num = 1
    chapter = db.query(Chapter).filter(
        Chapter.novel_id == novel.id, 
        Chapter.chapter_number == chapter_num
    ).first()
    
    # 텍스트 로드
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
        
    if not chapter:
        chapter = Chapter(
            novel_id=novel.id,
            chapter_number=chapter_num,
            title="Whole Text",
            content=text[:100] + "..." # 일부만 저장 (실제 텍스트는 파일에서 읽음)
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        print(f"  ✅ 챕터 생성 완료 (ID: {chapter.id})")
    else:
        # 내용 업데이트 (코퍼스 파일이 변경되었을 수 있으므로)
        chapter.content = text[:200] + "..."
        db.commit()
        print(f"  ℹ️ 챕터 업데이트 (ID: {chapter.id})")
    
    # 3. 씬 청킹 및 벡터화
    # 이미 벡터가 있는지 확인하지 않고 덮어씀 (EmbeddingSearchEngine이 처리)
    chunker = SceneChunker()
    scenes = chunker.split_into_scenes(text)
    print(f"  ✂️ 씬 분할 완료: {len(scenes)}개 씬")
    
    # 문서 데이터 구성
    documents = []
    for i, scene_text in enumerate(scenes):
        documents.append({
            "scene_index": i + 1,
            "original_text": scene_text,
            "summary": f"Scene {i+1} of {title}", # 요약 생성은 생략 (비용 문제)
            "novel_id": novel.id,
            "chapter_id": chapter.id
        })
    
    # 4. Pinecone 업로드
    engine = EmbeddingSearchEngine()
    try:
        engine.add_documents(documents, novel.id, chapter.id)
    except Exception as e:
        print(f"  ❌ 벡터 업로드 실패: {e}")


def main():
    db = SessionLocal()
    try:
        # 유저 확인
        user = get_or_create_user(db)
        
        # 코퍼스 파일 목록
        files = glob.glob(os.path.join(CORPUS_DIR, "*.txt"))
        if not files:
            print(f"❌ '{CORPUS_DIR}' 폴더에 텍스트 파일이 없습니다.")
            return

        print(f"🚀 총 {len(files)}개 소설 파일 업로드 시작...")
        
        for filepath in tqdm(files):
            try:
                process_novel(db, filepath, user.id)
            except Exception as e:
                print(f"❌ 파일 처리 중 오류 발생 ({filepath}): {e}")
                import traceback
                traceback.print_exc()

        print("\n✨ 모든 작업 완료!")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
