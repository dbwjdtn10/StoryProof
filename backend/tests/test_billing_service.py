"""정산(인보이스) 자동화 회귀 테스트 (2026-07-13)

api_usage_logs 집계 → 인보이스 계산이 올바른지, 동일 기간 재생성 시
중복 없이 갱신되는지, 비활성 파트너는 일괄 생성 대상에서 제외되는지 검증.
"""

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.models import ApiUsageLog, Base, Invoice, Partner, User
from backend.services.billing_service import generate_invoice, generate_invoices_for_all_partners


def _make_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_partner(db, plan="pro", monthly_quota=100_000, is_active=True, name="테스트파트너"):
    user = User(email=f"{name}@partner.internal", username=name,
                hashed_password="x", is_active=True)
    db.add(user)
    db.flush()
    partner = Partner(
        name=name, contact_email="billing@test.com", plan=plan,
        monthly_quota=monthly_quota, is_active=is_active, user_id=user.id,
    )
    db.add(partner)
    db.commit()
    return partner


def _add_usage(db, partner, units, created_at):
    db.add(ApiUsageLog(
        partner_id=partner.id, endpoint="/manuscripts/qa", method="POST",
        units=units, status_code=200, created_at=created_at,
    ))
    db.commit()


class TestGenerateInvoice:
    def test_computes_overage_and_total_amount(self):
        db = _make_session()
        partner = _make_partner(db, plan="pro", monthly_quota=100)
        _add_usage(db, partner, 80, datetime(2026, 6, 15, tzinfo=timezone.utc))
        _add_usage(db, partner, 50, datetime(2026, 6, 20, tzinfo=timezone.utc))
        # 6월 범위 밖 사용량은 집계에서 제외되어야 함
        _add_usage(db, partner, 9999, datetime(2026, 7, 1, tzinfo=timezone.utc))

        invoice = generate_invoice(db, partner, 2026, 6)

        assert invoice.total_units == 130
        assert invoice.included_units == 100
        assert invoice.overage_units == 30
        assert invoice.overage_unit_price_krw == 7  # pro 기본 단가
        assert invoice.overage_amount_krw == 210
        assert invoice.base_fee_krw == 500_000
        assert invoice.total_amount_krw == 500_210

    def test_no_overage_when_under_quota(self):
        db = _make_session()
        partner = _make_partner(db, plan="starter", monthly_quota=10_000)
        _add_usage(db, partner, 500, datetime(2026, 6, 1, tzinfo=timezone.utc))

        invoice = generate_invoice(db, partner, 2026, 6)

        assert invoice.overage_units == 0
        assert invoice.overage_amount_krw == 0
        assert invoice.total_amount_krw == invoice.base_fee_krw

    def test_regenerate_same_period_updates_not_duplicates(self):
        db = _make_session()
        partner = _make_partner(db, plan="pro", monthly_quota=100)
        _add_usage(db, partner, 50, datetime(2026, 6, 1, tzinfo=timezone.utc))

        first = generate_invoice(db, partner, 2026, 6)
        _add_usage(db, partner, 200, datetime(2026, 6, 2, tzinfo=timezone.utc))
        second = generate_invoice(db, partner, 2026, 6)

        assert first.id == second.id
        assert second.total_units == 250

        count = db.query(Invoice).filter(
            Invoice.partner_id == partner.id, Invoice.period_year == 2026, Invoice.period_month == 6
        ).count()
        assert count == 1

    def test_price_override_takes_precedence_over_plan_default(self):
        db = _make_session()
        partner = _make_partner(db, plan="pro", monthly_quota=0)
        _add_usage(db, partner, 10, datetime(2026, 6, 1, tzinfo=timezone.utc))

        invoice = generate_invoice(
            db, partner, 2026, 6, base_fee_krw=1_000, overage_unit_price_krw=100
        )

        assert invoice.base_fee_krw == 1_000
        assert invoice.overage_unit_price_krw == 100
        assert invoice.overage_amount_krw == 1_000  # 10 units * 100
        assert invoice.total_amount_krw == 2_000


class TestGenerateInvoicesForAllPartners:
    def test_skips_inactive_partners(self):
        db = _make_session()
        active = _make_partner(db, name="활성파트너", is_active=True)
        inactive = _make_partner(db, name="비활성파트너", is_active=False)
        _add_usage(db, active, 10, datetime(2026, 6, 1, tzinfo=timezone.utc))
        _add_usage(db, inactive, 10, datetime(2026, 6, 1, tzinfo=timezone.utc))

        invoices = generate_invoices_for_all_partners(db, 2026, 6)

        partner_ids = {inv.partner_id for inv in invoices}
        assert active.id in partner_ids
        assert inactive.id not in partner_ids
