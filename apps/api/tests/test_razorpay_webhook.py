"""Unit and integration tests for Razorpay payment creation, signature verification, and automated webhook freeze/unfreeze lifecycle."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
import pytest

from app.core.config import settings
from app.core.errors import ValidationError
from app.models.entities import CompanyTenant, PaymentTransaction, ProcessedWebhookEvent, SubscriptionPlan
from app.services.company_service import CompanyService
from app.services.email_service import EmailService
from app.services.razorpay_service import RazorpayService


@pytest.fixture
async def setup_test_company(test_db_session):
    """Fixture providing an active company tenant for payment testing."""
    service = CompanyService(test_db_session)
    from app.schemas.schemas import StudioSignupRequest
    req = StudioSignupRequest(
        company_name="Starlight Media",
        full_name="Stella Admin",
        email="stella@starlightmedia.com",
        password="SecurePassword2026!",
        plan_id="starter_studio",
    )
    await service.studio_signup(req)
    res = await test_db_session.execute(
        select(CompanyTenant).where(CompanyTenant.slug == "starlight-media")
    )
    return res.scalar_one()


from sqlalchemy import select


@pytest.mark.asyncio
async def test_razorpay_create_order(test_db_session, setup_test_company):
    """Test creating a Razorpay order records a PaymentTransaction with status CREATED."""
    company = setup_test_company
    service = RazorpayService(test_db_session)

    order_resp = await service.create_order(company=company, plan_id="pro_studio", extend_days=30)
    assert order_resp.order_id is not None
    assert order_resp.amount_paise > 0
    assert order_resp.currency == "INR"

    # Verify transaction record
    res_tx = await test_db_session.execute(
        select(PaymentTransaction).where(PaymentTransaction.razorpay_order_id == order_resp.order_id)
    )
    tx = res_tx.scalar_one_or_none()
    assert tx is not None
    assert tx.status == "CREATED"
    assert tx.plan_id == "pro_studio"
    assert tx.extend_days == 30


@pytest.mark.asyncio
async def test_razorpay_verify_payment_and_unfreeze(test_db_session, setup_test_company):
    """Test successful signature verification unfreezes company and extends subscription."""
    company = setup_test_company
    service = RazorpayService(test_db_session)

    # First freeze company
    company_service = CompanyService(test_db_session)
    await company_service.freeze_company(company.id, reason="Testing freeze")
    assert company.is_blocked is True
    assert company.subscription_status == "BLOCKED"

    # Create order and verify payment
    order_resp = await service.create_order(company=company, plan_id="pro_studio", extend_days=30)
    verify_resp = await service.verify_payment(
        company=company,
        order_id=order_resp.order_id,
        payment_id="pay_test_123456",
        signature="simulated_test_signature",
    )

    assert verify_resp.success is True
    assert verify_resp.subscription_status == "ACTIVE"
    assert company.is_blocked is False
    assert company.blocked_reason is None
    assert company.plan_id == "pro_studio"


@pytest.mark.asyncio
async def test_razorpay_verify_payment_signature_mismatch_fails(test_db_session, setup_test_company):
    """Test invalid signature is rejected with ValidationError when credentials are configured."""
    company = setup_test_company
    service = RazorpayService(test_db_session)

    # Temporarily mock configured keys
    orig_key = settings.RAZORPAY_KEY_ID
    orig_secret = settings.RAZORPAY_KEY_SECRET
    settings.RAZORPAY_KEY_ID = "rzp_test_real123"
    settings.RAZORPAY_KEY_SECRET = "secret_mock_456"

    try:
        # Create non-simulated transaction
        tx = PaymentTransaction(
            company_tenant_id=company.id,
            razorpay_order_id="order_real_999",
            amount_paise=249900,
            currency="INR",
            status="CREATED",
            plan_id="starter_studio",
            extend_days=30,
            details={},
        )
        test_db_session.add(tx)
        await test_db_session.commit()

        # Attempt verification with wrong signature
        with pytest.raises(ValidationError) as exc:
            await service.verify_payment(
                company=company,
                order_id="order_real_999",
                payment_id="pay_real_888",
                signature="invalid_tampered_signature",
            )
        assert "verification failed" in str(exc.value)
    finally:
        settings.RAZORPAY_KEY_ID = orig_key
        settings.RAZORPAY_KEY_SECRET = orig_secret


@pytest.mark.asyncio
async def test_razorpay_webhook_payment_captured_unfreezes_company(test_db_session, setup_test_company):
    """Test payment.captured webhook automatically unfreezes company and extends validity."""
    company = setup_test_company
    service = RazorpayService(test_db_session)

    # Freeze company
    company.is_blocked = True
    company.subscription_status = "BLOCKED"
    company.blocked_reason = "Manual hold"
    await test_db_session.commit()

    order_id = f"order_web_{uuid.uuid4().hex[:8]}"
    tx = PaymentTransaction(
        company_tenant_id=company.id,
        razorpay_order_id=order_id,
        amount_paise=249900,
        currency="INR",
        status="CREATED",
        plan_id="starter_studio",
        extend_days=30,
        details={},
    )
    test_db_session.add(tx)
    await test_db_session.commit()

    event_payload = {
        "event_id": f"evt_{uuid.uuid4().hex[:10]}",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_{uuid.uuid4().hex[:10]}",
                    "order_id": order_id,
                    "amount": 249900,
                    "status": "captured",
                    "notes": {"company_slug": company.slug},
                }
            }
        },
    }

    raw_body = json.dumps(event_payload).encode("utf-8")
    result = await service.process_webhook(raw_body=raw_body, signature_header=None)
    assert result["status"] == "success"

    await test_db_session.refresh(company)
    assert company.is_blocked is False
    assert company.subscription_status == "ACTIVE"
    assert company.blocked_reason is None


@pytest.mark.asyncio
async def test_razorpay_webhook_subscription_halted_freezes_company(test_db_session, setup_test_company):
    """Test subscription.halted webhook automatically freezes the company workspace."""
    company = setup_test_company
    service = RazorpayService(test_db_session)

    assert company.is_blocked is False
    assert company.subscription_status == "ACTIVE"

    event_payload = {
        "event_id": f"evt_halt_{uuid.uuid4().hex[:10]}",
        "event": "subscription.halted",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_123456",
                    "status": "halted",
                    "notes": {"company_slug": company.slug},
                }
            }
        },
    }

    raw_body = json.dumps(event_payload).encode("utf-8")
    result = await service.process_webhook(raw_body=raw_body, signature_header=None)
    assert result["status"] == "success"

    await test_db_session.refresh(company)
    assert company.is_blocked is True
    assert company.subscription_status == "BLOCKED"
    assert "subscription.halted" in company.blocked_reason


@pytest.mark.asyncio
async def test_razorpay_webhook_idempotency_prevents_duplicate_processing(test_db_session, setup_test_company):
    """Test duplicate webhook delivery with identical event_id is acknowledged without re-processing."""
    service = RazorpayService(test_db_session)
    event_id = f"evt_idem_{uuid.uuid4().hex[:10]}"

    event_payload = {
        "event_id": event_id,
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fail_1",
                    "error_description": "Card expired",
                }
            }
        },
    }

    raw_body = json.dumps(event_payload).encode("utf-8")

    # First delivery
    res1 = await service.process_webhook(raw_body=raw_body, signature_header=None)
    assert res1["status"] == "success"

    # Duplicate delivery
    res2 = await service.process_webhook(raw_body=raw_body, signature_header=None)
    assert res2["status"] == "already_processed"


def test_themed_email_templates_render():
    """Verify that EmailService generates valid HTML with BlogPilot design system elements."""
    email_service = EmailService()
    html = email_service._wrap_html_template(
        title="Payment Verified",
        status_badge="✓ Unlocked",
        status_badge_color="#15803d",
        status_badge_bg="#dcfce7",
        content_html="<p>Test workspace is unlocked.</p>",
        cta_text="Open Studio",
        cta_url="http://localhost:3000/dashboard",
    )
    assert "✦ BlogPilot" in html
    assert "linear-gradient" in html
    assert "Open Studio" in html
    assert "http://localhost:3000/dashboard" in html


@pytest.mark.asyncio
async def test_razorpay_signup_order_and_provisioning_with_payment(test_db_session):
    """Test creating signup order and provisioning studio with linked payment transaction."""
    from app.schemas.schemas import StudioSignupRequest
    service = RazorpayService(test_db_session)
    company_service = CompanyService(test_db_session)

    # 1. Create signup order
    order_resp = await service.create_signup_order(
        company_name="Nova Orbit Labs",
        email="founder@novaorbit.io",
        plan_id="pro_studio",
    )
    assert order_resp.order_id is not None
    assert order_resp.amount_paise > 0
    assert order_resp.company_name == "Nova Orbit Labs"

    # 2. Complete signup with razorpay payment details
    signup_req = StudioSignupRequest(
        company_name="Nova Orbit Labs",
        full_name="Neil Founder",
        email="founder@novaorbit.io",
        password="SecurePass2026!",
        plan_id="pro_studio",
        razorpay_order_id=order_resp.order_id,
        razorpay_payment_id="pay_signup_success_999",
        razorpay_signature="simulated_test_signature",
    )
    token_resp = await company_service.studio_signup(signup_req)
    assert token_resp.access_token is not None

    # 3. Verify PaymentTransaction linked to newly created company
    res_company = await test_db_session.execute(
        select(CompanyTenant).where(CompanyTenant.slug == "nova-orbit-labs")
    )
    company = res_company.scalar_one()

    txs = await service.list_transactions(company.id)
    assert len(txs) >= 1
    captured_tx = next((t for t in txs if t.razorpay_order_id == order_resp.order_id), None)
    assert captured_tx is not None
    assert captured_tx.status == "CAPTURED"
    assert captured_tx.razorpay_payment_id == "pay_signup_success_999"
    assert captured_tx.plan_id == "pro_studio"
    assert captured_tx.amount_paise == order_resp.amount_paise

    # 4. Verify printable receipt generation
    receipt_html = await service.generate_receipt_html(
        transaction_id=captured_tx.id,
        user_company=company,
    )
    assert "BlogPilot Studio" in receipt_html
    assert "Nova Orbit Labs" in receipt_html
    assert "pay_signup_success_999" in receipt_html
    assert "INV-" in receipt_html
    assert "CAPTURED" in receipt_html
    assert "window.print()" in receipt_html

