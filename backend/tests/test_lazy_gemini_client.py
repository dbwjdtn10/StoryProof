"""_LazyGeminiClient truthiness 회귀 테스트 (2026-07-13 코드리뷰에서 발견)

__bool__ 미정의 시 프록시 인스턴스가 항상 truthy라 `if not client:` 가드가
GOOGLE_API_KEY 미설정 상황을 감지하지 못하던 버그. 이제는 실제 초기화를
트리거하지 않고 "초기화 가능 여부"를 반환해야 한다.
"""

import backend.api.v1.endpoints.character_chat as character_chat_mod


def test_client_is_falsy_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(character_chat_mod.settings, "GOOGLE_API_KEY", None)
    assert not character_chat_mod.client
    assert bool(character_chat_mod.client) is False


def test_client_is_falsy_when_genai_unavailable(monkeypatch):
    monkeypatch.setattr(character_chat_mod, "genai", None)
    monkeypatch.setattr(character_chat_mod.settings, "GOOGLE_API_KEY", "fake-key")
    assert not character_chat_mod.client


def test_client_is_truthy_when_configured(monkeypatch):
    monkeypatch.setattr(character_chat_mod.settings, "GOOGLE_API_KEY", "fake-key")
    if character_chat_mod.genai is None:
        monkeypatch.setattr(character_chat_mod, "genai", object())
    assert bool(character_chat_mod.client) is True


def test_bool_check_does_not_trigger_real_initialization(monkeypatch):
    """__bool__ 평가 자체가 genai.Client(...)를 생성해선 안 된다 (부작용 없음)."""
    monkeypatch.setattr(character_chat_mod, "_client", None)
    monkeypatch.setattr(character_chat_mod.settings, "GOOGLE_API_KEY", None)

    bool(character_chat_mod.client)

    assert character_chat_mod._client is None
