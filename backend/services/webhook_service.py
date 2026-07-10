"""
파트너 웹훅 알림 서비스
=====================
원고 처리/분석 완료 이벤트를 파트너 서버로 push하여 폴링을 제거한다.

- 페이로드: JSON {event, manuscript_id, external_id, data, timestamp}
- 서명: HMAC-SHA256(webhook_secret, body) → `X-StoryProof-Signature: sha256=<hex>`
- 전송 실패 시 지수 백오프로 최대 3회 재시도 (실패해도 본 작업에는 영향 없음)
- 외부 의존성 없이 표준 라이브러리(urllib)만 사용
"""

import hashlib
import hmac
import json
import logging
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.db.models import Novel, Partner

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5
WEBHOOK_MAX_ATTEMPTS = 3

_EXTERNAL_ID_PATTERN = re.compile(r"\[external_id:([^\]]+)\]")


def extract_external_id(description: Optional[str]) -> Optional[str]:
    """소설 설명에 태깅된 파트너 측 작품 ID 추출"""
    if not description:
        return None
    match = _EXTERNAL_ID_PATTERN.search(description)
    return match.group(1) if match else None


def sign_payload(secret: str, body: bytes) -> str:
    """웹훅 페이로드 HMAC-SHA256 서명 생성"""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def deliver_webhook(url: str, secret: str, event: str, payload: Dict[str, Any]) -> bool:
    """웹훅 1건 전송 (재시도 포함). 성공 여부 반환."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "StoryProof-Webhook/1.0",
        "X-StoryProof-Event": event,
        "X-StoryProof-Signature": sign_payload(secret, body),
    }

    for attempt in range(1, WEBHOOK_MAX_ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=WEBHOOK_TIMEOUT_SECONDS) as response:
                if 200 <= response.status < 300:
                    logger.info(f"[Webhook] Delivered {event} to {url} (attempt {attempt})")
                    return True
                logger.warning(f"[Webhook] {url} responded {response.status} (attempt {attempt})")
        except Exception as e:
            logger.warning(f"[Webhook] Delivery failed to {url} (attempt {attempt}): {e}")

        if attempt < WEBHOOK_MAX_ATTEMPTS:
            time.sleep(2 ** attempt)  # 2s, 4s

    logger.error(f"[Webhook] Gave up delivering {event} to {url} after {WEBHOOK_MAX_ATTEMPTS} attempts")
    return False


def notify_partner_event(
    db: Session,
    novel_id: int,
    event: str,
    data: Dict[str, Any],
) -> bool:
    """소설 소유자가 웹훅을 설정한 파트너이면 이벤트를 전송

    Celery 태스크 완료 지점에서 호출된다. 파트너 소유가 아니거나
    웹훅 미설정이면 조용히 넘어간다 (일반 사용자 소설에는 영향 없음).

    이벤트 종류:
      manuscript.chapter.completed / manuscript.chapter.failed
      analysis.consistency.completed / analysis.consistency.failed
    """
    try:
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            return False

        partner = db.query(Partner).filter(Partner.user_id == novel.author_id).first()
        if not partner or not partner.is_active or not partner.webhook_url or not partner.webhook_secret:
            return False

        payload = {
            "event": event,
            "manuscript_id": novel.id,
            "external_id": extract_external_id(novel.description),
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return deliver_webhook(partner.webhook_url, partner.webhook_secret, event, payload)
    except Exception as e:
        # 웹훅 실패가 본 작업(분석 처리)을 깨뜨리면 안 됨
        logger.error(f"[Webhook] notify_partner_event error (novel={novel_id}, event={event}): {e}")
        return False
