"""정산(인보이스) 서비스

파트너별 월간 api_usage_logs를 집계해 인보이스를 생성한다.
단가는 core.config.settings.BILLING_PLAN_PRICING(임시값)을 사용하되,
호출 시 override 가능 — 실제 계약 단가가 정해지기 전까지의 유연성 확보용.
"""

import calendar
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.models import ApiUsageLog, Invoice, Partner

logger = logging.getLogger(__name__)


def _period_range(year: int, month: int):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    return start, end


def generate_invoice(
    db: Session,
    partner: Partner,
    year: int,
    month: int,
    base_fee_krw: Optional[int] = None,
    overage_unit_price_krw: Optional[int] = None,
) -> Invoice:
    """파트너의 특정 연월 인보이스를 생성/재생성한다 (동일 기간 재호출 시 갱신, 중복 생성 안 함)."""
    start, end = _period_range(year, month)

    total_units = db.query(
        sa_func.coalesce(sa_func.sum(ApiUsageLog.units), 0)
    ).filter(
        ApiUsageLog.partner_id == partner.id,
        ApiUsageLog.created_at >= start,
        ApiUsageLog.created_at <= end,
    ).scalar()
    total_units = int(total_units or 0)

    pricing = settings.BILLING_PLAN_PRICING.get(partner.plan, {"base_fee_krw": 0, "overage_unit_price_krw": 0})
    base_fee = base_fee_krw if base_fee_krw is not None else pricing["base_fee_krw"]
    overage_price = overage_unit_price_krw if overage_unit_price_krw is not None else pricing["overage_unit_price_krw"]

    included_units = partner.monthly_quota
    overage_units = max(0, total_units - included_units)
    overage_amount = overage_units * overage_price
    total_amount = base_fee + overage_amount

    invoice = db.query(Invoice).filter(
        Invoice.partner_id == partner.id,
        Invoice.period_year == year,
        Invoice.period_month == month,
    ).first()

    if not invoice:
        invoice = Invoice(partner_id=partner.id, period_year=year, period_month=month)
        db.add(invoice)

    invoice.plan = partner.plan
    invoice.total_units = total_units
    invoice.included_units = included_units
    invoice.overage_units = overage_units
    invoice.base_fee_krw = base_fee
    invoice.overage_unit_price_krw = overage_price
    invoice.overage_amount_krw = overage_amount
    invoice.total_amount_krw = total_amount

    db.commit()
    db.refresh(invoice)
    logger.info(
        f"인보이스 생성: partner={partner.name} {year}-{month:02d} "
        f"총 {total_units}units(포함 {included_units}, 초과 {overage_units}) → {total_amount}원"
    )
    return invoice


def generate_invoices_for_all_partners(db: Session, year: int, month: int) -> list:
    """모든 활성 파트너에 대해 해당 연월 인보이스를 일괄 생성한다 (월별 정산 자동화용)."""
    partners = db.query(Partner).filter(Partner.is_active == True).all()  # noqa: E712
    invoices = []
    for partner in partners:
        try:
            invoices.append(generate_invoice(db, partner, year, month))
        except Exception as e:
            logger.error(f"인보이스 생성 실패 (partner={partner.name}): {e}")
    return invoices
