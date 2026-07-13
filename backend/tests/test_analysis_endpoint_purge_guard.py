"""회차 분석 API — 콘텐츠 삭제된 챕터 요청 차단 회귀 테스트 (2026-07-13)

2026-07-13 코드리뷰에서 발견: 콘텐츠 보안 계약으로 원문이 삭제된 챕터에
plot/style/overall 분석을 요청하면 빈 텍스트로 LLM을 호출해 무의미한
결과를 캐싱하던 문제. request_chapter_analysis가 요청 단계에서 차단하는지
직접 함수 호출로 검증한다 (Celery/TestClient 없이).
"""

import types
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.v1.endpoints.analysis import request_chapter_analysis
from backend.db.models import Base, Chapter, Novel
from backend.schemas.analysis_schema import ChapterAnalysisRequest


def _make_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_blocks_analysis_request_for_purged_chapter(monkeypatch):
    db = _make_session()
    novel = Novel(title="테스트 소설", author_id=1)
    db.add(novel)
    db.flush()
    chapter = Chapter(
        novel_id=novel.id, chapter_number=1, title="1화", content="",
        content_purged=True,
    )
    db.add(chapter)
    db.commit()

    delay_mock = MagicMock()
    monkeypatch.setattr("backend.api.v1.endpoints.analysis.analyze_chapter_task", MagicMock(delay=delay_mock))

    current_user = types.SimpleNamespace(id=1)
    request = ChapterAnalysisRequest(novel_id=novel.id, chapter_id=chapter.id, analysis_type="plot")

    with pytest.raises(HTTPException) as exc_info:
        request_chapter_analysis(request, current_user=current_user, db=db)

    assert exc_info.value.status_code == 409
    delay_mock.assert_not_called()


def test_allows_analysis_request_for_intact_chapter(monkeypatch):
    db = _make_session()
    novel = Novel(title="테스트 소설", author_id=1)
    db.add(novel)
    db.flush()
    chapter = Chapter(
        novel_id=novel.id, chapter_number=1, title="1화", content="정상적인 본문",
        content_purged=False,
    )
    db.add(chapter)
    db.commit()

    delay_mock = MagicMock(return_value=types.SimpleNamespace(id="task-1"))
    monkeypatch.setattr("backend.api.v1.endpoints.analysis.analyze_chapter_task", MagicMock(delay=delay_mock))

    current_user = types.SimpleNamespace(id=1)
    request = ChapterAnalysisRequest(novel_id=novel.id, chapter_id=chapter.id, analysis_type="plot")

    result = request_chapter_analysis(request, current_user=current_user, db=db)

    assert result["status"] == "PENDING"
    delay_mock.assert_called_once()
