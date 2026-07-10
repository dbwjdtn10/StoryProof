"""
부하테스트용 서버 하네스
=======================
외부 의존성(LLM/Celery/Pinecone/Redis) 없이 API 계층만 측정하기 위한 실행기.

스텁 처리 (측정에서 제외되는 것):
  - Gemini LLM 호출  → 고정 응답 반환 (LLM_STUB_DELAY_MS 환경변수로 지연 시뮬레이션 가능)
  - Celery 태스크    → no-op (원고 접수 API의 큐잉 오버헤드만 측정)
  - DB               → SQLite(WAL) 파일. 프로덕션 PostgreSQL 대비 쓰기 직렬화로
                       보수적(불리한) 수치가 나옴을 SLA 문서에 명시할 것.

실측되는 것: FastAPI 라우팅/직렬화, JWT·API키 인증, 테넌트 격리 쿼리,
             사용량 계측 INSERT, 쿼터 집계 쿼리.

사용법:
  python scripts/loadtest/server_harness.py [port]
  → 시드 정보(API 키/토큰 등)를 scripts/loadtest/seed.json 에 기록 후 서빙
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "loadtest.db")
SEED_PATH = os.path.join(HERE, "seed.json")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
LLM_STUB_DELAY_MS = int(os.environ.get("LLM_STUB_DELAY_MS", "0"))


def rebind_database():
    """전역 엔진을 SQLite(WAL)로 교체 (FastAPI threadpool 대응)"""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    import backend.db.session as session_mod
    from backend.db.models import Base

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    # pool_size 주의: 프로덕션 기본값(5+10)으로는 동시성 50에서 풀 고갈로
    # 30초 대기/타임아웃 발생 (부하테스트 실측). 운영 시 DB_POOL_SIZE 상향 필요.
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
        pool_size=60,
        max_overflow=40,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    session_mod.engine = engine
    session_mod.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(engine)
    return session_mod


def stub_external_services():
    """LLM/Celery를 스텁으로 교체"""
    import backend.services.chatbot_service as chatbot_mod

    class StubChatbot:
        def warmup(self):
            pass

        def ask(self, **kwargs):
            if LLM_STUB_DELAY_MS > 0:
                time.sleep(LLM_STUB_DELAY_MS / 1000)
            return {
                "answer": "[부하테스트 스텁] 위드는 조각사가 되어 사냥을 시작했습니다.",
                "source": None,
                "similarity": 0.85,
                "found_context": True,
            }

    chatbot_mod.get_chatbot_service = lambda: StubChatbot()

    from backend.worker import tasks as tasks_mod
    tasks_mod.process_chapter_storyboard.delay = lambda *a, **k: None
    tasks_mod.detect_inconsistency_task.delay = lambda *a, **k: None


def seed_data(session_mod):
    """부하테스트용 파트너/원고/토큰 시드"""
    import secrets
    from backend.db.models import User, Partner, PartnerApiKey, Novel, Chapter
    from backend.core.security import hash_password
    from backend.core.partner_auth import generate_api_key
    from backend.core.widget_auth import create_widget_session_token

    db = session_mod.SessionLocal()

    user = User(
        email="loadtest@partner.internal", username="partner_loadtest",
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        is_active=True, is_verified=True,
    )
    db.add(user)
    db.flush()

    partner = Partner(
        name="부하테스트파트너", contact_email="load@test.com",
        plan="enterprise",
        monthly_quota=1_000_000_000,        # 테스트 중 쿼터 초과 방지
        rate_limit_per_minute=1_000_000_000,
        user_id=user.id,
    )
    db.add(partner)
    db.flush()

    raw_key, key_hash, key_prefix = generate_api_key()
    db.add(PartnerApiKey(partner_id=partner.id, name="loadtest",
                         key_prefix=key_prefix, key_hash=key_hash))

    novel = Novel(title="부하테스트 소설", author_id=user.id, is_public=False)
    db.add(novel)
    db.flush()
    chapter = Chapter(novel_id=novel.id, chapter_number=1, title="1화",
                      content="본문 " * 200, word_count=200,
                      storyboard_status="COMPLETED", storyboard_progress=100)
    db.add(chapter)
    db.commit()

    widget_token, _ = create_widget_session_token(
        partner_id=partner.id, manuscript_id=novel.id,
        chapter_id=chapter.id, ttl_minutes=24 * 60,
    )
    seed = {
        "base_url": f"http://127.0.0.1:{PORT}",
        "api_key": raw_key,
        "manuscript_id": novel.id,
        "chapter_id": chapter.id,
        "widget_token": widget_token,
        "llm_stub_delay_ms": LLM_STUB_DELAY_MS,
        "pid": os.getpid(),
    }
    db.close()

    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=2)
    print(f"[harness] seed written: {SEED_PATH}")


def main():
    session_mod = rebind_database()
    stub_external_services()
    seed_data(session_mod)

    import uvicorn
    from backend.main import app
    print(f"[harness] serving on 127.0.0.1:{PORT} (LLM stub delay: {LLM_STUB_DELAY_MS}ms)")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
