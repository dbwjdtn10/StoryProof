"""LLM 비용 최적화 — 콘텐츠 해시 기반 캐싱 회귀 테스트 (2026-07-13)

3개 경로에서 동일 콘텐츠 재요청 시 LLM을 다시 호출하지 않고 기존 결과를
재사용하는지 검증한다:
1. NovelService.analyze_chapter — 스토리보드 구조화(씬분할+구조화, N+2회 호출)
2. analyze_chapter_task — 회차 분석(plot/style/overall)
3. detect_inconsistency_task — 설정 일관성 검사

Pinecone/Redis/실 Gemini 호출 없이 순수 캐시 판단 로직만 검증한다.
실행: pytest backend/tests/test_llm_caching.py -v
"""

import hashlib
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import Analysis, AnalysisStatus, AnalysisType, Base, Chapter


@pytest.fixture
def db_session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # Analysis.result는 JSONB().with_variant(JSON(), "sqlite")라 SQLite에서도 그대로 생성 가능
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


class TestStoryboardReanalysisSkip:
    """NovelService.analyze_chapter: 내용 불변 시 process_chapter_storyboard 큐잉 자체를 건너뛴다."""

    def test_skips_when_content_hash_matches_completed(self, db_session_factory, monkeypatch):
        import backend.services.novel_service as novel_service_mod

        db = db_session_factory()
        content = "1화 본문입니다."
        chapter = Chapter(
            novel_id=1, chapter_number=1, title="1화", content=content,
            storyboard_status="COMPLETED",
            storyboard_content_hash=hashlib.sha256(content.encode('utf-8')).hexdigest(),
        )
        db.add(chapter)
        db.commit()

        monkeypatch.setattr(
            novel_service_mod.NovelService, "get_chapter",
            staticmethod(lambda db_, novel_id, chapter_id, user_id, is_admin=False: chapter),
        )

        delay_mock = MagicMock()
        monkeypatch.setattr(
            "backend.worker.tasks.process_chapter_storyboard",
            MagicMock(delay=delay_mock),
        )

        result = novel_service_mod.NovelService.analyze_chapter(db, 1, chapter.id, user_id=1)

        assert result["status"] == "skipped"
        delay_mock.assert_not_called()

    def test_reruns_when_content_changed(self, db_session_factory, monkeypatch):
        import backend.services.novel_service as novel_service_mod

        db = db_session_factory()
        old_content = "1화 본문입니다."
        chapter = Chapter(
            novel_id=1, chapter_number=1, title="1화", content="1화 수정된 본문입니다.",
            storyboard_status="COMPLETED",
            storyboard_content_hash=hashlib.sha256(old_content.encode('utf-8')).hexdigest(),
        )
        db.add(chapter)
        db.commit()

        monkeypatch.setattr(
            novel_service_mod.NovelService, "get_chapter",
            staticmethod(lambda db_, novel_id, chapter_id, user_id, is_admin=False: chapter),
        )

        delay_mock = MagicMock()
        monkeypatch.setattr(
            "backend.worker.tasks.process_chapter_storyboard",
            MagicMock(delay=delay_mock),
        )

        result = novel_service_mod.NovelService.analyze_chapter(db, 1, chapter.id, user_id=1)

        assert result["status"] == "accepted"
        delay_mock.assert_called_once_with(1, chapter.id)

    def test_blocks_reanalysis_when_content_purged(self, db_session_factory, monkeypatch):
        """회귀 테스트(2026-07-13 코드리뷰에서 발견): 콘텐츠 보안 계약으로 원문이
        삭제된 챕터(content="", content_purged=True)를 재분석 요청하면, 해시
        불일치로 파이프라인이 재실행되어 남은 벡터 인덱스까지 삭제되던 버그.
        이제는 content_purged 플래그로 즉시 차단해야 한다."""
        import backend.services.novel_service as novel_service_mod

        db = db_session_factory()
        original_content = "원래 있던 민감한 원문"
        chapter = Chapter(
            novel_id=1, chapter_number=1, title="1화", content="",  # 삭제됨
            storyboard_status="COMPLETED",
            storyboard_content_hash=hashlib.sha256(original_content.encode('utf-8')).hexdigest(),
            content_purged=True,
        )
        db.add(chapter)
        db.commit()

        monkeypatch.setattr(
            novel_service_mod.NovelService, "get_chapter",
            staticmethod(lambda db_, novel_id, chapter_id, user_id, is_admin=False: chapter),
        )

        delay_mock = MagicMock()
        monkeypatch.setattr(
            "backend.worker.tasks.process_chapter_storyboard",
            MagicMock(delay=delay_mock),
        )

        result = novel_service_mod.NovelService.analyze_chapter(db, 1, chapter.id, user_id=1)

        assert result["status"] == "blocked"
        delay_mock.assert_not_called()  # 파이프라인이 재실행되면 안 됨 (기존 벡터 인덱스 보존)


class TestChapterAnalysisTaskCache:
    """analyze_chapter_task: 동일 회차·동일 텍스트·동일 유형이면 에이전트 호출을 생략한다."""

    def test_cache_hit_skips_agent_call(self, db_session_factory, monkeypatch):
        import backend.worker.tasks as tasks_mod

        monkeypatch.setattr(tasks_mod, "SessionLocal", db_session_factory)
        db = db_session_factory()

        text = "회차 본문 내용"
        chapter = Chapter(novel_id=1, chapter_number=1, title="1화", content=text)
        db.add(chapter)
        db.commit()

        content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        prior = Analysis(
            novel_id=1, chapter_id=chapter.id, analysis_type=AnalysisType.PLOT,
            status=AnalysisStatus.COMPLETED, result={"summary": "cached-result"},
            content_hash=content_hash,
        )
        new = Analysis(
            novel_id=1, chapter_id=chapter.id, analysis_type=AnalysisType.PLOT,
            status=AnalysisStatus.PENDING,
        )
        db.add_all([prior, new])
        db.commit()

        fake_agent = MagicMock()
        monkeypatch.setattr(
            "backend.services.agent.get_consistency_agent", lambda: fake_agent
        )

        result = tasks_mod.analyze_chapter_task.run(new.id, 1, chapter.id, "plot")

        assert result == {"summary": "cached-result"}
        fake_agent.analyze_plot.assert_not_called()

        # 태스크가 내부적으로 여는 세션과 분리된 새 세션으로 영속화를 확인
        verify_db = db_session_factory()
        refreshed = verify_db.query(Analysis).filter(Analysis.id == new.id).first()
        assert refreshed.status == AnalysisStatus.COMPLETED
        assert refreshed.result == {"summary": "cached-result"}
        verify_db.close()

    def test_cache_miss_calls_agent(self, db_session_factory, monkeypatch):
        import backend.worker.tasks as tasks_mod

        monkeypatch.setattr(tasks_mod, "SessionLocal", db_session_factory)
        db = db_session_factory()

        text = "이번엔 처음 보는 본문"
        chapter = Chapter(novel_id=1, chapter_number=1, title="1화", content=text)
        db.add(chapter)
        db.commit()

        new = Analysis(
            novel_id=1, chapter_id=chapter.id, analysis_type=AnalysisType.PLOT,
            status=AnalysisStatus.PENDING,
        )
        db.add(new)
        db.commit()

        fake_agent = MagicMock()
        fake_agent.analyze_plot.return_value = {"summary": "fresh-result"}
        monkeypatch.setattr(
            "backend.services.agent.get_consistency_agent", lambda: fake_agent
        )

        result = tasks_mod.analyze_chapter_task.run(new.id, 1, chapter.id, "plot")

        assert result == {"summary": "fresh-result"}
        fake_agent.analyze_plot.assert_called_once()


class TestConsistencyTaskCache:
    """detect_inconsistency_task: 동일 회차·동일 텍스트면 재검사를 생략한다."""

    def test_cache_hit_skips_consistency_check(self, db_session_factory, monkeypatch):
        import backend.worker.tasks as tasks_mod

        monkeypatch.setattr(tasks_mod, "SessionLocal", db_session_factory)
        db = db_session_factory()

        text_fragment = "검토할 문장입니다."
        content_hash = hashlib.sha256(text_fragment.encode('utf-8')).hexdigest()
        prior = Analysis(
            novel_id=1, chapter_id=1, analysis_type=AnalysisType.CONSISTENCY,
            status=AnalysisStatus.COMPLETED, result={"issues": []},
            content_hash=content_hash,
        )
        new = Analysis(
            novel_id=1, chapter_id=1, analysis_type=AnalysisType.CONSISTENCY,
            status=AnalysisStatus.PENDING,
        )
        db.add_all([prior, new])
        db.commit()

        fake_agent = MagicMock()
        monkeypatch.setattr(
            "backend.services.agent.get_consistency_agent", lambda: fake_agent
        )
        monkeypatch.setattr(
            "backend.services.webhook_service.notify_partner_event", MagicMock()
        )

        result = tasks_mod.detect_inconsistency_task.run(
            1, text_fragment, chapter_id=1, analysis_id=new.id
        )

        assert result == {"issues": []}
        fake_agent.check_consistency.assert_not_called()
