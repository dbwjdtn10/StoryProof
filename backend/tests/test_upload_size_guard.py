"""파트너 원고 업로드 — Content-Length 사전 거부 회귀 테스트 (2026-07-13 코드리뷰)

기존에는 `await file.read()`로 전체 파일을 메모리에 올린 뒤에야 크기를
검사해, 대용량 업로드가 OOM을 유발할 수 있었다. Content-Length 헤더가
한도를 초과하면 파일을 읽지 않고 즉시 거부해야 한다.
"""

import types
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from backend.api.partner.v1 import upload_manuscript_file
from backend.core.config import settings


def _make_request(content_length):
    return types.SimpleNamespace(headers={"content-length": str(content_length)} if content_length else {})


def _make_file(filename="novel.txt"):
    f = types.SimpleNamespace(filename=filename)
    f.read = AsyncMock(side_effect=AssertionError("file.read()가 호출되면 안 됨 (사전 거부 실패)"))
    f.seek = AsyncMock()
    return f


@pytest.mark.anyio
async def test_rejects_oversized_upload_without_reading_body():
    request = _make_request(settings.MAX_UPLOAD_SIZE + 1)
    file = _make_file()

    with pytest.raises(HTTPException) as exc_info:
        await upload_manuscript_file(
            request=request, file=file, title=None, genre=None, external_id=None,
            ctx=None, db=None,
        )

    assert exc_info.value.status_code == 413
    file.read.assert_not_called()


@pytest.mark.anyio
async def test_allows_upload_when_content_length_missing_or_small():
    # content-length 헤더가 없으면(청크 전송 등) 사전 검사를 건너뛰고
    # 기존 read()-후-검사 경로로 진행해야 한다 (file.read() 호출까지는 도달)
    request = _make_request(None)
    file = _make_file()

    with pytest.raises(AssertionError):
        await upload_manuscript_file(
            request=request, file=file, title=None, genre=None, external_id=None,
            ctx=None, db=None,
        )
    file.read.assert_called_once()
