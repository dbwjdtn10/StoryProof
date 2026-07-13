"""파트너(B2B) API 통합 테스트

SQLite in-memory + TestClient 기반. Celery/Redis/Pinecone 불필요.
실행: pytest backend/tests/test_partner_api.py -v
"""

import pytest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.db.models import Base, User, Partner
from backend.db.session import get_db
from backend.core.security import hash_password, create_access_token
from backend.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)


def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    # analyses 테이블은 PostgreSQL 전용 JSONB를 사용하므로 제외
    tables = [t for name, t in Base.metadata.tables.items() if name != "analyses"]
    Base.metadata.create_all(bind=engine, tables=tables)
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def admin_headers(client):
    db = TestingSession()
    admin = User(email="admin@test.com", username="admin",
                 hashed_password=hash_password("x"), is_admin=True, is_active=True)
    db.add(admin)
    db.commit()
    db.refresh(admin)
    token = create_access_token({"sub": str(admin.id)})
    db.close()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def partner(client, admin_headers):
    """파트너 등록 후 (partner_id, api_key) 반환"""
    r = client.post("/api/v1/admin/partners/", headers=admin_headers, json={
        "name": "테스트플랫폼", "contact_email": "biz@test-platform.com",
        "plan": "pro", "monthly_quota": 1000, "rate_limit_per_minute": 100,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    return data["partner"]["id"], data["api_key"]


def test_partner_creation_returns_raw_key(partner):
    _, api_key = partner
    assert api_key.startswith("sp_live_")


def test_partner_deployment_region_defaults_and_override(client, admin_headers):
    r = client.post("/api/v1/admin/partners/", headers=admin_headers, json={
        "name": "리전기본값파트너", "contact_email": "shared@test.com",
    })
    assert r.status_code == 201, r.text
    assert r.json()["partner"]["deployment_region"] == "shared"
    assert r.json()["partner"]["content_retention_mode"] == "full"

    r2 = client.post("/api/v1/admin/partners/", headers=admin_headers, json={
        "name": "전용리전파트너", "contact_email": "dedicated@test.com",
        "deployment_region": "ap-northeast-2-dedicated",
        "dedicated_instance_url": "https://partner-x.api.storyproof.com",
        "content_retention_mode": "minimal",
    })
    assert r2.status_code == 201, r2.text
    partner_out = r2.json()["partner"]
    assert partner_out["deployment_region"] == "ap-northeast-2-dedicated"
    assert partner_out["dedicated_instance_url"] == "https://partner-x.api.storyproof.com"
    assert partner_out["content_retention_mode"] == "minimal"


def test_non_admin_cannot_create_partner(client):
    db = TestingSession()
    user = User(email="u@test.com", username="user1", hashed_password=hash_password("x"))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    db.close()

    r = client.post("/api/v1/admin/partners/",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"name": "x", "contact_email": "a@b.co"})
    assert r.status_code == 403


def test_api_key_auth(client, partner):
    _, api_key = partner
    assert client.get("/api/partner/v1/usage", headers={"X-API-Key": api_key}).status_code == 200
    assert client.get("/api/partner/v1/usage", headers={"X-API-Key": "sp_live_wrong"}).status_code == 401
    assert client.get("/api/partner/v1/usage").status_code == 401


def test_manuscript_ingest_and_usage_metering(client, partner):
    _, api_key = partner

    with patch("backend.worker.tasks.process_chapter_storyboard.delay") as mock_delay:
        r = client.post("/api/partner/v1/manuscripts", headers={"X-API-Key": api_key}, json={
            "title": "테스트 소설", "genre": "판타지", "external_id": "ext-1",
            "chapters": [
                {"chapter_number": 1, "title": "1화", "content": "본문1"},
                {"chapter_number": 2, "title": "2화", "content": "본문2"},
            ],
        })
    assert r.status_code == 202, r.text
    body = r.json()
    assert len(body["chapter_ids"]) == 2
    assert mock_delay.call_count == 2

    # 상태 조회 (처리 전이므로 ready=False)
    ms_id = body["manuscript_id"]
    r = client.get(f"/api/partner/v1/manuscripts/{ms_id}/status", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    assert r.json()["ready"] is False

    # 사용량: 회차당 1 unit → 2 units 기록
    r = client.get("/api/partner/v1/usage", headers={"X-API-Key": api_key})
    assert r.json()["used_this_month"] == 2


def test_tenant_isolation(client, admin_headers, partner):
    """다른 파트너의 원고에는 접근 불가"""
    _, api_key = partner

    with patch("backend.worker.tasks.process_chapter_storyboard.delay"):
        ms_id = client.post("/api/partner/v1/manuscripts", headers={"X-API-Key": api_key}, json={
            "title": "격리 테스트", "chapters": [{"chapter_number": 1, "title": "1화", "content": "x"}],
        }).json()["manuscript_id"]

    r2 = client.post("/api/v1/admin/partners/", headers=admin_headers, json={
        "name": "다른파트너", "contact_email": "other@test.com",
    })
    other_key = r2.json()["api_key"]

    r = client.get(f"/api/partner/v1/manuscripts/{ms_id}/status", headers={"X-API-Key": other_key})
    assert r.status_code == 404


def test_key_rotation_and_revocation(client, admin_headers, partner):
    partner_id, _ = partner

    r = client.post(f"/api/v1/admin/partners/{partner_id}/keys?name=rotation", headers=admin_headers)
    assert r.status_code == 201
    new_key = r.json()["api_key"]
    new_key_id = r.json()["key_info"]["id"]

    assert client.get("/api/partner/v1/usage", headers={"X-API-Key": new_key}).status_code == 200

    # 키 목록 조회 (원본 키/해시 미노출, prefix만)
    r = client.get(f"/api/v1/admin/partners/{partner_id}/keys", headers=admin_headers)
    assert r.status_code == 200
    listed = r.json()
    assert any(k["id"] == new_key_id and k["is_active"] for k in listed)
    assert all("key_hash" not in k and "api_key" not in k for k in listed)

    r = client.delete(f"/api/v1/admin/partners/{partner_id}/keys/{new_key_id}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get("/api/partner/v1/usage", headers={"X-API-Key": new_key}).status_code == 401

    # 폐기된 키는 목록에서 is_active=false로 표시
    r = client.get(f"/api/v1/admin/partners/{partner_id}/keys", headers=admin_headers)
    revoked = next(k for k in r.json() if k["id"] == new_key_id)
    assert revoked["is_active"] is False


def test_webhook_configure_and_remove(client, partner):
    _, api_key = partner
    headers = {"X-API-Key": api_key}

    # 등록 → secret 1회 노출
    r = client.put("/api/partner/v1/webhook", headers=headers,
                   json={"url": "https://partner.example.com/callbacks/storyproof"})
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    assert len(secret) == 64

    # 조회 → configured, secret 미노출
    r = client.get("/api/partner/v1/webhook", headers=headers)
    assert r.json() == {
        "url": "https://partner.example.com/callbacks/storyproof",
        "configured": True,
    }

    # http(s) 외 URL 거부
    r = client.put("/api/partner/v1/webhook", headers=headers, json={"url": "ftp://x"})
    assert r.status_code == 422

    # 해제
    assert client.delete("/api/partner/v1/webhook", headers=headers).status_code == 204
    assert client.get("/api/partner/v1/webhook", headers=headers).json()["configured"] is False


def test_webhook_notify_partner_event(client, partner):
    """파트너 원고의 처리 완료 이벤트가 서명된 웹훅으로 전송되는지 검증"""
    from backend.services import webhook_service
    from backend.services.webhook_service import notify_partner_event, sign_payload

    _, api_key = partner
    headers = {"X-API-Key": api_key}

    client.put("/api/partner/v1/webhook", headers=headers,
               json={"url": "https://partner.example.com/hook"})

    with patch("backend.worker.tasks.process_chapter_storyboard.delay"):
        ms = client.post("/api/partner/v1/manuscripts", headers=headers, json={
            "title": "웹훅 테스트", "external_id": "wh-001",
            "chapters": [{"chapter_number": 1, "title": "1화", "content": "본문"}],
        }).json()

    db = TestingSession()
    try:
        with patch.object(webhook_service, "deliver_webhook", return_value=True) as mock_deliver:
            sent = notify_partner_event(db, ms["manuscript_id"], "manuscript.chapter.completed", {
                "chapter_id": ms["chapter_ids"][0], "status": "COMPLETED",
            })
        assert sent is True
        url, secret, event, payload = mock_deliver.call_args.args
        assert url == "https://partner.example.com/hook"
        assert event == "manuscript.chapter.completed"
        assert payload["manuscript_id"] == ms["manuscript_id"]
        assert payload["external_id"] == "wh-001"  # description 태그에서 복원

        # 일반 사용자 소설(파트너 아님)은 전송되지 않음
        assert notify_partner_event(db, 999999, "manuscript.chapter.completed", {}) is False
    finally:
        db.close()

    # 서명 형식 검증 (HMAC-SHA256)
    import hashlib, hmac as hmac_mod
    body = b'{"event":"x"}'
    expected = "sha256=" + hmac_mod.new(b"secret", body, hashlib.sha256).hexdigest()
    assert sign_payload("secret", body) == expected


def test_epub_manuscript_upload(client, partner):
    """EPUB 업로드 → spine 문서 단위 자동 회차 분리"""
    from backend.tests.test_epub_loader import _build_epub

    _, api_key = partner

    with patch("backend.worker.tasks.process_chapter_storyboard.delay") as mock_delay:
        r = client.post(
            "/api/partner/v1/manuscripts/upload",
            headers={"X-API-Key": api_key},
            files={"file": ("book.epub", _build_epub(), "application/epub+zip")},
            data={"title": "EPUB 소설", "external_id": "epub-001"},
        )
    assert r.status_code == 202, r.text
    body = r.json()
    assert len(body["chapter_ids"]) == 2  # spine 문서 2개 → 회차 2개
    assert body["external_id"] == "epub-001"
    assert mock_delay.call_count == 2

    # 지원하지 않는 확장자 거부
    r = client.post(
        "/api/partner/v1/manuscripts/upload",
        headers={"X-API-Key": api_key},
        files={"file": ("book.hwp", b"x", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_widget_session_and_qa(client, admin_headers, partner):
    """위젯 세션 토큰 발급 → 브라우저 Q&A → 파트너 과금 귀속 검증"""
    _, api_key = partner

    with patch("backend.worker.tasks.process_chapter_storyboard.delay"):
        ms = client.post("/api/partner/v1/manuscripts", headers={"X-API-Key": api_key}, json={
            "title": "위젯 테스트", "chapters": [
                {"chapter_number": 1, "title": "1화", "content": "본문1"},
            ],
        }).json()

    # 1. 세션 발급 (회차 상한 지정)
    r = client.post("/api/partner/v1/widget-sessions", headers={"X-API-Key": api_key},
                    json={"manuscript_id": ms["manuscript_id"],
                          "chapter_id": ms["chapter_ids"][0], "ttl_minutes": 30})
    assert r.status_code == 200, r.text
    session = r.json()
    assert session["expires_in"] == 30 * 60
    token = session["token"]

    # 1-1. 타 파트너 원고로는 발급 불가 (테넌트 격리)
    other_key = client.post("/api/v1/admin/partners/", headers=admin_headers, json={
        "name": "위젯격리파트너", "contact_email": "w@x.co",
    }).json()["api_key"]
    r = client.post("/api/partner/v1/widget-sessions", headers={"X-API-Key": other_key},
                    json={"manuscript_id": ms["manuscript_id"]})
    assert r.status_code == 404

    # 2. 위젯 Q&A (LLM은 mock) — 토큰의 회차 상한이 강제되는지 확인
    before = client.get("/api/partner/v1/usage",
                        headers={"X-API-Key": api_key}).json()["used_this_month"]

    mock_chatbot = MagicMock()
    mock_chatbot.ask.return_value = {
        "answer": "위드는 조각사가 되었습니다.", "found_context": True, "similarity": 0.9,
    }
    with patch("backend.services.chatbot_service.get_chatbot_service", return_value=mock_chatbot):
        r = client.post("/api/widget/v1/qa",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"question": "주인공은 누구야?"})
    assert r.status_code == 200, r.text
    assert r.json()["answer"] == "위드는 조각사가 되었습니다."
    assert mock_chatbot.ask.call_args.kwargs["novel_id"] == ms["manuscript_id"]
    assert mock_chatbot.ask.call_args.kwargs["chapter_id"] == ms["chapter_ids"][0]

    # 3. 과금이 파트너에게 귀속 (1 unit 증가)
    after = client.get("/api/partner/v1/usage",
                       headers={"X-API-Key": api_key}).json()["used_this_month"]
    assert after == before + 1

    # 4. 메타 조회 (무과금)
    r = client.get("/api/widget/v1/meta", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["title"] == "위젯 테스트"

    # 5. 잘못된 토큰들 거부
    assert client.post("/api/widget/v1/qa", json={"question": "x"}).status_code in (401, 403)
    assert client.post("/api/widget/v1/qa", headers={"Authorization": "Bearer invalid"},
                       json={"question": "x"}).status_code == 401
    # 일반 사용자 JWT는 scope가 widget이 아니므로 거부
    user_jwt = create_access_token({"sub": "1"})
    assert client.post("/api/widget/v1/qa", headers={"Authorization": f"Bearer {user_jwt}"},
                       json={"question": "x"}).status_code == 401


def test_widget_cors_preflight(client):
    """파트너 도메인에서의 preflight가 위젯 경로에서 허용되는지"""
    r = client.options("/api/widget/v1/qa", headers={
        "Origin": "https://some-random-partner.com",
        "Access-Control-Request-Method": "POST",
    })
    assert r.status_code == 204
    assert r.headers.get("access-control-allow-origin") == "*"
    assert "Authorization" in r.headers.get("access-control-allow-headers", "")


def test_monthly_quota_exceeded(client, partner):
    partner_id, api_key = partner

    db = TestingSession()
    p = db.query(Partner).filter(Partner.id == partner_id).first()
    p.monthly_quota = 1  # 이미 사용량이 있으므로 즉시 초과
    db.commit()
    db.close()

    r = client.get("/api/partner/v1/usage", headers={"X-API-Key": api_key})
    assert r.status_code == 429
