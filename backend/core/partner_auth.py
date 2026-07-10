"""
파트너(B2B) API 인증 및 사용량 관리
- API 키 발급/검증 (SHA-256 해시 저장, 원본 키는 발급 시 1회만 노출)
- 월간 쿼터 및 분당 레이트 리밋 검사
- 사용량 로깅 (과금 근거)
"""

import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import Partner, PartnerApiKey, ApiUsageLog

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

KEY_PREFIX = "sp_live_"


# ===== 키 발급/해싱 =====

def generate_api_key() -> Tuple[str, str, str]:
    """새 API 키 생성

    Returns:
        (raw_key, key_hash, key_prefix)
        raw_key는 발급 응답에서 1회만 노출되고 DB에는 해시만 저장된다.
    """
    raw_key = KEY_PREFIX + secrets.token_hex(24)
    return raw_key, hash_api_key(raw_key), raw_key[:12]


def hash_api_key(raw_key: str) -> str:
    """API 키 SHA-256 해시"""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


# ===== 인증 의존성 =====

class PartnerContext:
    """인증된 파트너 요청 컨텍스트"""

    def __init__(self, partner: Partner, api_key: PartnerApiKey):
        self.partner = partner
        self.api_key = api_key


# Redis 클라이언트 재사용 + 서킷 브레이커
# (요청마다 새 연결을 만들면 Redis 장애 시 요청당 ~2초 연결 타임아웃이 붙어
#  스레드풀이 포화됨 — 부하테스트에서 실측 확인. 장애 감지 후 일정 시간
#  재시도를 건너뛰어 Redis 다운이 API 전체 지연으로 번지지 않게 한다)
_redis_client = None
_redis_down_until = 0.0
_REDIS_RETRY_INTERVAL_SECONDS = 30.0


def _get_redis_client():
    global _redis_client
    if _redis_client is None:
        import redis
        from backend.core.config import settings
        _redis_client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _redis_client


def _check_rate_limit(partner: Partner) -> None:
    """분당 레이트 리밋 검사 (Redis 사용, Redis 불가 시 통과)"""
    global _redis_down_until
    import time as _time

    if _time.monotonic() < _redis_down_until:
        return  # 서킷 열림 — Redis 복구 재시도 대기 중

    try:
        client = _get_redis_client()
        bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        key = f"partner_rl:{partner.id}:{bucket}"
        count = client.incr(key)
        if count == 1:
            client.expire(key, 90)
        if count > partner.rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="분당 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            )
    except HTTPException:
        raise
    except Exception as e:
        # 레이트 리밋은 fail-open (Redis 장애가 API 전체 장애로 번지지 않도록)
        _redis_down_until = _time.monotonic() + _REDIS_RETRY_INTERVAL_SECONDS
        logger.warning(
            f"Rate limit check skipped (redis unavailable, retry in "
            f"{_REDIS_RETRY_INTERVAL_SECONDS}s): {e}"
        )


def _check_monthly_quota(db: Session, partner: Partner) -> None:
    """월간 사용량 쿼터 검사"""
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    used = db.query(sa_func.coalesce(sa_func.sum(ApiUsageLog.units), 0)).filter(
        ApiUsageLog.partner_id == partner.id,
        ApiUsageLog.created_at >= month_start,
    ).scalar()
    if used >= partner.monthly_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"이번 달 API 사용 한도({partner.monthly_quota})를 초과했습니다. 플랜 업그레이드가 필요합니다.",
        )


async def get_current_partner(
    api_key: Optional[str] = Depends(API_KEY_HEADER),
    db: Session = Depends(get_db),
) -> PartnerContext:
    """X-API-Key 헤더로 파트너 인증 (의존성 주입용)

    검증 순서: 키 존재 → 해시 매칭 → 키/파트너 활성 → 만료 → 레이트 리밋 → 월간 쿼터
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key 헤더가 필요합니다.",
        )

    key_row = db.query(PartnerApiKey).filter(
        PartnerApiKey.key_hash == hash_api_key(api_key)
    ).first()

    if not key_row or not key_row.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API 키입니다.",
        )

    if key_row.expires_at is not None:
        expires_at = key_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="만료된 API 키입니다.",
            )

    partner = db.query(Partner).filter(Partner.id == key_row.partner_id).first()
    if not partner or not partner.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 파트너 계정입니다.",
        )

    _check_rate_limit(partner)
    _check_monthly_quota(db, partner)

    key_row.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return PartnerContext(partner=partner, api_key=key_row)


# ===== 사용량 로깅 =====

def log_api_usage(
    db: Session,
    ctx: PartnerContext,
    endpoint: str,
    method: str = "POST",
    units: int = 1,
    status_code: int = 200,
) -> None:
    """API 사용량 기록 (과금 근거). 실패해도 요청 자체는 성공 처리."""
    try:
        db.add(ApiUsageLog(
            partner_id=ctx.partner.id,
            api_key_id=ctx.api_key.id,
            endpoint=endpoint,
            method=method,
            units=units,
            status_code=status_code,
        ))
        db.commit()
    except Exception as e:
        logger.error(f"API 사용량 로깅 실패 (partner={ctx.partner.id}, endpoint={endpoint}): {e}")
        db.rollback()
