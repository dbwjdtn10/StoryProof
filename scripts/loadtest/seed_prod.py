"""
프로덕션(Docker+PostgreSQL) 스택용 부하테스트 시드
====================================================
server_harness.py와 달리 DB를 새로 만들지 않고, 이미 떠 있는 앱의
DATABASE_URL(컨테이너 내부에서는 postgres db 서비스)에 그대로 시드 데이터를 심는다.

사용법 (api 컨테이너 안에서 실행):
  docker compose exec api python -m scripts.loadtest.seed_prod
"""

import json
import os
import secrets

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(HERE, "seed.json")
BASE_URL = os.environ.get("LOADTEST_BASE_URL", "http://localhost:8000")


def main():
    from backend.db.session import SessionLocal
    from backend.db.models import User, Partner, PartnerApiKey, Novel, Chapter
    from backend.core.security import hash_password
    from backend.core.partner_auth import generate_api_key
    from backend.core.widget_auth import create_widget_session_token

    db = SessionLocal()

    user = User(
        email="loadtest@partner.internal", username="partner_loadtest_prod",
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        is_active=True, is_verified=True,
    )
    db.add(user)
    db.flush()

    partner = Partner(
        name="부하테스트파트너(prod)", contact_email="load@test.com",
        plan="enterprise",
        monthly_quota=1_000_000_000,
        rate_limit_per_minute=1_000_000_000,
        user_id=user.id,
    )
    db.add(partner)
    db.flush()

    raw_key, key_hash, key_prefix = generate_api_key()
    db.add(PartnerApiKey(partner_id=partner.id, name="loadtest-prod",
                          key_prefix=key_prefix, key_hash=key_hash))

    novel = Novel(title="부하테스트 소설(prod)", author_id=user.id, is_public=False)
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
        "base_url": BASE_URL,
        "api_key": raw_key,
        "manuscript_id": novel.id,
        "chapter_id": chapter.id,
        "widget_token": widget_token,
        "pid": os.getpid(),
    }
    db.close()

    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(seed, f, ensure_ascii=False, indent=2)
    print(f"[seed_prod] seed written: {SEED_PATH}")


if __name__ == "__main__":
    main()
