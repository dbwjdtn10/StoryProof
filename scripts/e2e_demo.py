"""
End-to-End 데모 (Redis/Celery/Docker 불필요)
============================================
실제 Gemini + Pinecone + 로컬 임베딩으로 전체 파이프라인을 시연한다.

  1. 파트너/원고 시드 (SQLite)
  2. 스토리보드 분석 — Celery 태스크를 동기 실행 (씬 분할 → 구조화 → 임베딩)
  3. RAG Q&A — 파트너/위젯 API가 쓰는 것과 동일한 챗봇 서비스로 질의

사용법: python scripts/e2e_demo.py
전제:  .env에 GOOGLE_API_KEY / PINECONE_API_KEY 설정
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "e2e_demo.db")

DEMO_STORY = """
달빛이 공방의 창을 넘어 들어왔다. 위드는 조각칼을 내려놓고 이마의 땀을 닦았다.
그의 손에는 방금 완성한 달의 여신상이 들려 있었다. 은은한 빛이 조각상에서 흘러나왔다.

"드디어... 걸작이 나왔군."

위드는 왕국 제일의 조각사가 되기 위해 로자임 왕국의 수도를 떠나 3년째 방랑 중이었다.
그의 스승 자흐렌은 떠나는 그에게 낡은 조각칼 하나를 건네며 말했었다.
"조각은 손이 아니라 마음으로 하는 것이다. 네가 그것을 깨닫는 날, 이 칼이 대답할 것이다."

그날 밤, 여관에서 위드는 이상한 꿈을 꾸었다. 달의 여신 헤스티아가 나타나 속삭였다.
"나의 모습을 새긴 자여, 그대에게 달빛 조각술을 허락하노라."

깨어난 위드의 손에는 스승의 조각칼이 푸른 달빛으로 빛나고 있었다.
공방 밖에서는 왕국 기사단장 페일이 그를 찾아와 문을 두드리고 있었다.
"위드 님, 국왕 폐하께서 왕궁 대전에 세울 조각상을 의뢰하고자 하십니다."

위드는 조각칼을 쥐었다. 새로운 이야기가 시작되고 있었다.
""".strip()

QUESTIONS = [
    "위드의 스승은 누구야?",
    "위드가 꿈에서 만난 존재는?",
    "페일은 왜 위드를 찾아왔어?",
]


def step(msg):
    print(f"\n{'=' * 60}\n[STEP] {msg}\n{'=' * 60}", flush=True)


def rebind_sqlite():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import backend.db.session as session_mod
    from backend.db.models import Base

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    session_mod.engine = engine
    session_mod.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)
    return session_mod


def main():
    from backend.core.config import settings
    if not settings.GOOGLE_API_KEY or not settings.PINECONE_API_KEY:
        print("[ERROR] .env에 GOOGLE_API_KEY / PINECONE_API_KEY를 설정하세요.")
        sys.exit(1)

    session_mod = rebind_sqlite()

    # ---- 1. 시드 ----
    step("1/3 원고 접수 (파트너 원고 시드)")
    import secrets
    from backend.db.models import User, Partner, Novel, Chapter
    from backend.core.security import hash_password

    db = session_mod.SessionLocal()
    user = User(email="demo@partner.internal", username="partner_demo",
                hashed_password=hash_password(secrets.token_urlsafe(16)),
                is_active=True, is_verified=True)
    db.add(user); db.flush()
    partner = Partner(name="데모파트너", contact_email="demo@x.co", user_id=user.id)
    db.add(partner); db.flush()
    novel = Novel(title="달빛 조각사 (데모)", author_id=user.id,
                  description="[external_id:demo-001]")
    db.add(novel); db.flush()
    chapter = Chapter(novel_id=novel.id, chapter_number=1, title="1화. 달빛 조각술",
                      content=DEMO_STORY, word_count=len(DEMO_STORY),
                      storyboard_status="PENDING")
    db.add(chapter); db.commit()
    novel_id, chapter_id = novel.id, chapter.id
    db.close()
    print(f"원고 접수 완료: manuscript_id={novel_id}, chapter_id={chapter_id}, {len(DEMO_STORY)}자")

    # ---- 2. 스토리보드 분석 (Celery 태스크 동기 실행) ----
    step("2/3 스토리보드 분석 — 씬 분할 → 구조화(Gemini) → 임베딩(Pinecone)")
    t0 = time.time()
    from backend.worker.tasks import process_chapter_storyboard
    process_chapter_storyboard(novel_id, chapter_id)  # .delay 대신 동기 호출

    db = session_mod.SessionLocal()
    ch = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    print(f"\n처리 상태: {ch.storyboard_status} ({ch.storyboard_message}) — {time.time() - t0:.1f}초 소요")
    if ch.storyboard_status != "COMPLETED":
        print(f"[ERROR] 분석 실패: {ch.storyboard_error}")
        db.close()
        sys.exit(1)
    db.close()

    # Pinecone 반영 대기 (serverless 인덱스는 upsert 반영에 수 초 지연)
    print("Pinecone 인덱스 반영 대기 (10초)...")
    time.sleep(10)

    # ---- 3. RAG Q&A ----
    step("3/3 RAG Q&A — 파트너/위젯 API와 동일한 경로")
    # 2026-07-13: 소규모 코퍼스 dense-only 폴백(SEARCH_MIN_BM25_CORPUS_SIZE)과
    # e5 query:/passage: 프리픽스 수정으로, 단일 회차 데모에서도 기본 게이트
    # (0.55)를 그대로 통과한다 — 더 이상 게이트를 낮출 필요 없음.
    from backend.services.chatbot_service import get_chatbot_service
    chatbot = get_chatbot_service()

    db = session_mod.SessionLocal()
    for q in QUESTIONS:
        t0 = time.time()
        result = chatbot.ask(question=q, alpha=0.7, similarity_threshold=0.2,
                             novel_id=novel_id, chapter_id=None, novel_filter=None, db=db)
        elapsed = time.time() - t0
        print(f"\nQ: {q}")
        print(f"A: {result.get('answer', '').strip()}")
        print(f"   (유사도 {result.get('similarity', 0):.2f}, "
              f"근거발견 {result.get('found_context')}, {elapsed:.1f}초)")
    db.close()

    print(f"\n{'=' * 60}\n[DONE] End-to-End 데모 완료\n{'=' * 60}")


if __name__ == "__main__":
    main()
