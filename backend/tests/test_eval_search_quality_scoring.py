"""검색 품질 평가 하네스의 채점 로직 유닛 테스트 (2026-07-13)

scripts/eval_search_quality.py의 score()는 실 Gemini 호출 없이도 그
자체로 올바른지 검증 가능한 순수 로직이다 — 실행 전에 반드시 확인.
"""

import importlib.util
import os

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "eval_search_quality",
    os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "eval_search_quality.py"),
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
score = _MOD.score


def _qa(expect, keywords=None):
    return {"expect": expect, "expected_keywords": keywords or []}


class TestScoreFoundCases:
    def test_passes_when_context_found_and_keyword_present(self):
        qa = _qa("found", ["자흐렌"])
        result = {"found_context": True, "answer": "위드의 스승은 자흐렌입니다."}
        passed, reason = score(qa, result)
        assert passed is True
        assert reason == ""

    def test_fails_when_context_not_found(self):
        qa = _qa("found", ["자흐렌"])
        result = {"found_context": False, "answer": "찾을 수 없습니다."}
        passed, reason = score(qa, result)
        assert passed is False
        assert "근거" in reason

    def test_fails_when_context_found_but_keyword_missing(self):
        qa = _qa("found", ["자흐렌"])
        result = {"found_context": True, "answer": "위드의 스승은 언급되지 않았습니다."}
        passed, reason = score(qa, result)
        assert passed is False
        assert "키워드" in reason

    def test_passes_with_any_one_of_multiple_keywords(self):
        qa = _qa("found", ["헤스티아", "여신"])
        result = {"found_context": True, "answer": "달의 여신이 나타났다."}
        passed, _ = score(qa, result)
        assert passed is True


class TestScoreNotFoundCases:
    def test_passes_when_context_correctly_not_found(self):
        qa = _qa("not_found")
        result = {"found_context": False, "answer": "찾을 수 없습니다."}
        passed, reason = score(qa, result)
        assert passed is True
        assert reason == ""

    def test_fails_when_context_incorrectly_found(self):
        """스포일러 회차필터 누수 또는 환각 — 가장 심각한 실패 유형."""
        qa = _qa("not_found")
        result = {"found_context": True, "answer": "왕실 조각사입니다."}
        passed, reason = score(qa, result)
        assert passed is False
        assert "환각" in reason or "누수" in reason
