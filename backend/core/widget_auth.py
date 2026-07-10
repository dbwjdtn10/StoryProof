"""
위젯 세션 토큰 인증
==================
파트너 API 키를 브라우저에 노출하지 않기 위한 단기 세션 토큰 계층.

흐름:
  1. 파트너 서버가 API 키로 POST /api/partner/v1/widget-sessions 호출
  2. 작품/회차 범위가 고정된 JWT 세션 토큰 발급 (기본 30분)
  3. 브라우저 위젯이 이 토큰으로 POST /api/widget/v1/qa 호출
  4. 토큰의 partner_id로 사용량 계측/쿼터/레이트 리밋이 파트너에게 귀속

토큰에 chapter_id가 있으면 위젯은 해당 회차까지만 질문 가능 (스포일러 방지).
"""

import logging
from datetime import timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.core.security import create_access_token, decode_token
from backend.core.partner_auth import _check_rate_limit, _check_monthly_quota
from backend.db.session import get_db
from backend.db.models import Partner

logger = logging.getLogger(__name__)

WIDGET_TOKEN_SCOPE = "widget"
DEFAULT_TTL_MINUTES = 30
MAX_TTL_MINUTES = 24 * 60

_bearer = HTTPBearer(auto_error=False)


def create_widget_session_token(
    partner_id: int,
    manuscript_id: int,
    chapter_id: Optional[int] = None,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> tuple[str, int]:
    """위젯 세션 토큰 생성. (token, expires_in_seconds) 반환"""
    ttl_minutes = max(1, min(ttl_minutes, MAX_TTL_MINUTES))
    payload = {
        "scope": WIDGET_TOKEN_SCOPE,
        "partner_id": partner_id,
        "manuscript_id": manuscript_id,
        "chapter_id": chapter_id,
    }
    token = create_access_token(payload, expires_delta=timedelta(minutes=ttl_minutes))
    return token, ttl_minutes * 60


class WidgetContext:
    """검증된 위젯 요청 컨텍스트"""

    def __init__(self, partner: Partner, manuscript_id: int, chapter_id: Optional[int]):
        self.partner = partner
        self.manuscript_id = manuscript_id
        self.chapter_id = chapter_id


async def get_widget_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> WidgetContext:
    """위젯 세션 토큰 검증 (의존성 주입용)

    검증 순서: 토큰 존재 → JWT 서명/만료 → scope → 파트너 활성
             → 레이트 리밋 → 월간 쿼터
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="위젯 세션 토큰이 필요합니다.",
        )

    payload = decode_token(credentials.credentials)  # 서명/만료 검증 (실패 시 401)

    if payload.get("scope") != WIDGET_TOKEN_SCOPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="위젯 세션 토큰이 아닙니다.",
        )

    partner = db.query(Partner).filter(Partner.id == payload.get("partner_id")).first()
    if not partner or not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 파트너입니다.",
        )

    _check_rate_limit(partner)
    _check_monthly_quota(db, partner)

    return WidgetContext(
        partner=partner,
        manuscript_id=int(payload["manuscript_id"]),
        chapter_id=payload.get("chapter_id"),
    )
