"""
파트너 관리 API (관리자 전용)
- 파트너 등록 (서비스 계정 + 최초 API 키 자동 발급)
- API 키 추가 발급 / 폐기
- 파트너별 사용량 조회
"""

import re
import secrets
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models import User, Partner, PartnerApiKey, ApiUsageLog, Invoice
from backend.core.security import require_admin, hash_password
from backend.core.partner_auth import generate_api_key, get_current_month_start
from backend.services.billing_service import generate_invoice
from backend.schemas.partner_schema import (
    PartnerCreateRequest, PartnerCreateResponse, PartnerOut,
    ApiKeyOut, ApiKeyIssueResponse, InvoiceGenerateRequest, InvoiceOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "partner"


@router.post("/", response_model=PartnerCreateResponse, status_code=status.HTTP_201_CREATED)
def create_partner(
    request: PartnerCreateRequest,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """파트너 등록

    전용 서비스 계정(User)을 만들고 최초 API 키를 발급한다.
    응답의 api_key는 이 응답에서만 확인 가능하다 (DB에는 해시만 저장).
    """
    if db.query(Partner).filter(Partner.name == request.name).first():
        raise HTTPException(status_code=409, detail="이미 존재하는 파트너 이름입니다.")

    slug = _slugify(request.name)
    base_username = f"partner_{slug}"
    username = base_username
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        suffix += 1
        username = f"{base_username}{suffix}"

    service_user = User(
        email=f"{username}@partner.storyproof.internal",
        username=username,
        hashed_password=hash_password(secrets.token_urlsafe(32)),  # 로그인 불가 랜덤 비밀번호
        is_active=True,
        is_verified=True,
        user_mode="writer",
    )
    db.add(service_user)
    db.flush()

    partner = Partner(
        name=request.name,
        contact_email=request.contact_email,
        plan=request.plan,
        monthly_quota=request.monthly_quota,
        rate_limit_per_minute=request.rate_limit_per_minute,
        content_retention_mode=request.content_retention_mode,
        deployment_region=request.deployment_region,
        dedicated_instance_url=request.dedicated_instance_url,
        user_id=service_user.id,
    )
    db.add(partner)
    db.flush()

    raw_key, key_hash, key_prefix = generate_api_key()
    db.add(PartnerApiKey(
        partner_id=partner.id,
        name="default",
        key_prefix=key_prefix,
        key_hash=key_hash,
    ))
    db.commit()
    db.refresh(partner)

    logger.info(f"Partner created: {partner.name} (id={partner.id})")
    return PartnerCreateResponse(partner=PartnerOut.model_validate(partner), api_key=raw_key)


@router.get("/", response_model=list[PartnerOut])
def list_partners(
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """파트너 목록 조회"""
    return [PartnerOut.model_validate(p) for p in db.query(Partner).order_by(Partner.id).all()]


@router.get("/{partner_id}/keys", response_model=list[ApiKeyOut])
def list_api_keys(
    partner_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """파트너의 API 키 목록 조회 (해시/원본 키는 노출하지 않음)"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="파트너를 찾을 수 없습니다.")
    keys = db.query(PartnerApiKey).filter(
        PartnerApiKey.partner_id == partner_id
    ).order_by(PartnerApiKey.id).all()
    return [ApiKeyOut.model_validate(k) for k in keys]


@router.post("/{partner_id}/keys", response_model=ApiKeyIssueResponse,
             status_code=status.HTTP_201_CREATED)
def issue_api_key(
    partner_id: int,
    name: str = "default",
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """API 키 추가 발급 (키 로테이션용)"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="파트너를 찾을 수 없습니다.")

    raw_key, key_hash, key_prefix = generate_api_key()
    key_row = PartnerApiKey(
        partner_id=partner.id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
    )
    db.add(key_row)
    db.commit()
    db.refresh(key_row)

    return ApiKeyIssueResponse(key_info=ApiKeyOut.model_validate(key_row), api_key=raw_key)


@router.delete("/{partner_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    partner_id: int,
    key_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """API 키 폐기 (비활성화)"""
    key_row = db.query(PartnerApiKey).filter(
        PartnerApiKey.id == key_id,
        PartnerApiKey.partner_id == partner_id,
    ).first()
    if not key_row:
        raise HTTPException(status_code=404, detail="API 키를 찾을 수 없습니다.")
    key_row.is_active = False
    db.commit()


@router.get("/{partner_id}/usage")
def get_partner_usage(
    partner_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """파트너 사용량 조회 (이번 달, 엔드포인트별 집계)"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="파트너를 찾을 수 없습니다.")

    month_start = get_current_month_start()
    rows = db.query(
        ApiUsageLog.endpoint,
        sa_func.count(ApiUsageLog.id).label("calls"),
        sa_func.coalesce(sa_func.sum(ApiUsageLog.units), 0).label("units"),
    ).filter(
        ApiUsageLog.partner_id == partner_id,
        ApiUsageLog.created_at >= month_start,
    ).group_by(ApiUsageLog.endpoint).all()

    total_units = sum(int(r.units) for r in rows)
    return {
        "partner_id": partner_id,
        "partner_name": partner.name,
        "plan": partner.plan,
        "monthly_quota": partner.monthly_quota,
        "used_this_month": total_units,
        "by_endpoint": [
            {"endpoint": r.endpoint, "calls": int(r.calls), "units": int(r.units)}
            for r in rows
        ],
    }


# ===== 정산(인보이스) =====

@router.post("/{partner_id}/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def generate_partner_invoice(
    partner_id: int,
    request: InvoiceGenerateRequest,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """파트너의 특정 연월 인보이스를 생성/재생성한다.

    단가 미지정 시 플랜 기본 단가(BILLING_PLAN_PRICING, 임시값) 사용.
    동일 연월로 재호출하면 기존 인보이스를 최신 사용량으로 갱신한다(중복 생성 없음).
    """
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="파트너를 찾을 수 없습니다.")

    invoice = generate_invoice(
        db, partner, request.year, request.month,
        base_fee_krw=request.base_fee_krw,
        overage_unit_price_krw=request.overage_unit_price_krw,
    )
    return InvoiceOut.model_validate(invoice)


@router.get("/{partner_id}/invoices", response_model=list[InvoiceOut])
def list_partner_invoices(
    partner_id: int,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """파트너의 인보이스 이력 조회 (최신순)"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="파트너를 찾을 수 없습니다.")

    invoices = db.query(Invoice).filter(Invoice.partner_id == partner_id).order_by(
        Invoice.period_year.desc(), Invoice.period_month.desc()
    ).all()
    return [InvoiceOut.model_validate(inv) for inv in invoices]
