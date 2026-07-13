"""씬 구조화 배치 처리 유닛 테스트 (LLM 비용 최적화, 2026-07-13)

structure_scenes_batch()가 여러 씬을 한 번의 LLM 호출로 처리하고, 배치
응답이 기대와 다르면(개수 불일치/파싱 실패) 호출자가 씬별 폴백을 할 수
있도록 예외를 던지는지 검증한다. 실 Gemini/네트워크 호출 없음.
"""

import json
from unittest.mock import MagicMock

import pytest

from backend.services.analysis.gemini_structurer import GeminiStructurer, StructuredScene


def _make_structurer():
    # genai.Client(api_key=...)는 네트워크 호출 없이 클라이언트 객체만 생성함.
    # 실제 API 호출부(_generate_with_retry)는 각 테스트에서 개별적으로 mock 처리.
    return GeminiStructurer(api_key="test")


def _fake_response(payload):
    resp = MagicMock()
    resp.text = json.dumps(payload, ensure_ascii=False)
    return resp


class TestStructureScenesBatch:
    def test_parses_matching_length_array_in_order(self):
        structurer = _make_structurer()
        indexed_scenes = [(5, "다섯 번째 씬 본문"), (6, "여섯 번째 씬 본문")]
        payload = [
            {"summary": "요약5", "characters": [{"name": "위드"}]},
            {"summary": "요약6", "characters": []},
        ]
        structurer._generate_with_retry = MagicMock(return_value=_fake_response(payload))

        results = structurer.structure_scenes_batch(indexed_scenes)

        assert len(results) == 2
        assert all(isinstance(r, StructuredScene) for r in results)
        assert results[0].scene_index == 5
        assert results[0].summary == "요약5"
        assert results[0].original_text == "다섯 번째 씬 본문"
        assert results[1].scene_index == 6
        assert results[1].summary == "요약6"

    def test_strips_markdown_code_fence(self):
        structurer = _make_structurer()
        indexed_scenes = [(0, "씬 본문")]
        payload = [{"summary": "요약"}]
        resp = MagicMock()
        resp.text = "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"
        structurer._generate_with_retry = MagicMock(return_value=resp)

        results = structurer.structure_scenes_batch(indexed_scenes)

        assert results[0].summary == "요약"

    def test_length_mismatch_raises_for_caller_fallback(self):
        structurer = _make_structurer()
        indexed_scenes = [(0, "씬 A"), (1, "씬 B"), (2, "씬 C")]
        payload = [{"summary": "요약A"}]  # 3개 기대했는데 1개만 옴
        structurer._generate_with_retry = MagicMock(return_value=_fake_response(payload))

        with pytest.raises(ValueError):
            structurer.structure_scenes_batch(indexed_scenes)

    def test_non_list_response_raises_for_caller_fallback(self):
        structurer = _make_structurer()
        indexed_scenes = [(0, "씬 A")]
        structurer._generate_with_retry = MagicMock(
            return_value=_fake_response({"summary": "배열이 아니라 객체로 옴"})
        )

        with pytest.raises(ValueError):
            structurer.structure_scenes_batch(indexed_scenes)

    def test_non_dict_element_raises_for_caller_fallback(self):
        structurer = _make_structurer()
        indexed_scenes = [(0, "씬 A"), (1, "씬 B")]
        structurer._generate_with_retry = MagicMock(
            return_value=_fake_response(["문자열 원소", {"summary": "ok"}])
        )

        with pytest.raises(ValueError):
            structurer.structure_scenes_batch(indexed_scenes)
