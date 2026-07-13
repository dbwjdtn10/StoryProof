"""콘텐츠 보안 계약 대응 — 원문 보존 최소화 모드 회귀 테스트 (2026-07-13)

파트너의 content_retention_mode가 "minimal"이면 원고 처리 완료 시 원문
전체(Chapter.content)를 삭제하고, "full"(기본값)이거나 파트너 소유가
아니면(B2C 사용자) 그대로 보존하는지 검증한다.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Base, Chapter, Novel, Partner, User
from backend.worker.tasks import maybe_purge_chapter_content


def _make_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_user_novel_chapter(db, author_id=1):
    novel = Novel(title="테스트 소설", author_id=author_id)
    db.add(novel)
    db.flush()
    chapter = Chapter(novel_id=novel.id, chapter_number=1, title="1화", content="민감한 원문 내용")
    db.add(chapter)
    db.commit()
    return novel, chapter


class TestMaybePurgeChapterContent:
    def test_purges_when_partner_is_minimal_retention(self):
        db = _make_session()
        user = User(email="p@partner.internal", username="partner_x",
                    hashed_password="x", is_active=True)
        db.add(user)
        db.flush()
        partner = Partner(
            name="보안계약파트너", contact_email="sec@partner.com",
            content_retention_mode="minimal", user_id=user.id,
        )
        db.add(partner)
        db.commit()

        novel, chapter = _make_user_novel_chapter(db, author_id=user.id)

        purged = maybe_purge_chapter_content(db, novel, chapter, chapter.id)

        assert purged is True
        assert chapter.content == ""

    def test_keeps_content_when_partner_is_full_retention(self):
        db = _make_session()
        user = User(email="p2@partner.internal", username="partner_y",
                    hashed_password="x", is_active=True)
        db.add(user)
        db.flush()
        partner = Partner(
            name="일반파트너", contact_email="full@partner.com",
            content_retention_mode="full", user_id=user.id,
        )
        db.add(partner)
        db.commit()

        novel, chapter = _make_user_novel_chapter(db, author_id=user.id)

        purged = maybe_purge_chapter_content(db, novel, chapter, chapter.id)

        assert purged is False
        assert chapter.content == "민감한 원문 내용"

    def test_keeps_content_for_non_partner_b2c_novel(self):
        db = _make_session()
        user = User(email="writer@example.com", username="writer1",
                    hashed_password="x", is_active=True)
        db.add(user)
        db.commit()

        novel, chapter = _make_user_novel_chapter(db, author_id=user.id)

        purged = maybe_purge_chapter_content(db, novel, chapter, chapter.id)

        assert purged is False
        assert chapter.content == "민감한 원문 내용"

    def test_returns_false_when_novel_is_none(self):
        db = _make_session()
        _, chapter = _make_user_novel_chapter(db, author_id=1)

        purged = maybe_purge_chapter_content(db, None, chapter, chapter.id)

        assert purged is False
        assert chapter.content == "민감한 원문 내용"
