"""Production-grade Razorpay payment service and webhook lifecycle manager."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.logging import logger
from app.models.entities import (
    AuditLog,
    CompanyTenant,
    PaymentTransaction,
    ProcessedWebhookEvent,
    SubscriptionPlan,
)
from app.schemas.schemas import (
    PaymentTransactionOut,
    RazorpayOrderResponse,
    RazorpayVerifyPaymentResponse,
)
from app.services.email_service import EmailService


def calculate_amount_paise(plan: SubscriptionPlan, extend_days: int) -> int:
    """Calculate price in lowest currency denomination (paise for INR, cents for USD)."""
    months = max(1, round(extend_days / 30))
    currency = (settings.RAZORPAY_CURRENCY or "INR").upper()
    if currency == "INR":
        inr_price = int(plan.price_monthly_usd * 85)
        return inr_price * months * 100  # in paise
    # For USD or other non-INR currencies, amount is in cents (1 USD = 100 cents)
    return max(100, int(plan.price_monthly_usd * months * 100))


class RazorpayService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = EmailService()

    def is_configured(self) -> bool:
        """Check if production/test Razorpay API credentials are set."""
        return bool(
            settings.RAZORPAY_KEY_ID
            and settings.RAZORPAY_KEY_SECRET
            and not settings.RAZORPAY_KEY_ID.startswith("YOUR_")
            and not settings.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder")
        )

    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify HMAC-SHA256 signature against Razorpay key secret."""
        if not self.is_configured() or order_id.startswith("order_sim_"):
            return True
        if not signature or not payment_id:
            return False
        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)

    async def create_signup_order(
        self,
        company_name: str,
        email: str,
        plan_id: str,
    ) -> RazorpayOrderResponse:
        """Create a Razorpay order server-side for new studio signup before account provisioning."""
        from app.services.company_service import slugify
        company_slug = slugify(company_name)
        if not company_slug:
            raise ValidationError("A valid company name is required.")

        # Pre-validate uniqueness of company name and admin email
        existing_res = await self.db.execute(
            select(CompanyTenant).where(
                (CompanyTenant.slug == company_slug) | (CompanyTenant.admin_email == email.lower())
            )
        )
        if existing_res.scalar_one_or_none():
            raise ConflictError("A company with this name or admin email already exists.")

        res_plan = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        plan = res_plan.scalar_one_or_none()
        if not plan:
            raise NotFoundError("SubscriptionPlan", plan_id)

        extend_days = 30
        amount_paise = calculate_amount_paise(plan, extend_days)
        currency = settings.RAZORPAY_CURRENCY or "INR"

        order_id = f"order_sim_{uuid.uuid4().hex[:16]}"
        is_test_mode = not self.is_configured()

        if not is_test_mode:
            auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            payload = {
                "amount": amount_paise,
                "currency": currency,
                "receipt": f"rcpt_signup_{company_slug[:10]}_{uuid.uuid4().hex[:8]}",
                "notes": {
                    "company_name": company_name,
                    "company_slug": company_slug,
                    "plan_id": plan.id,
                    "extend_days": str(extend_days),
                    "admin_email": email.lower(),
                    "is_signup": "true",
                },
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post("https://api.razorpay.com/v1/orders", auth=auth, json=payload)
                if resp.status_code != 200:
                    logger.error(f"Razorpay signup order creation failed: {resp.text}")
                    raise ValidationError(f"Gateway error creating payment order: {resp.text}")
                order_data = resp.json()
                order_id = order_data["id"]
        else:
            logger.info(f"[RAZORPAY SIMULATION MODE] Created signup order {order_id} for company {company_name}")

        # Record pre-signup transaction with company_tenant_id=None
        tx = PaymentTransaction(
            company_tenant_id=None,
            razorpay_order_id=order_id,
            amount_paise=amount_paise,
            currency=currency,
            status="CREATED",
            plan_id=plan.id,
            extend_days=extend_days,
            details={
                "company_name": company_name,
                "admin_email": email.lower(),
                "plan_name": plan.name,
                "is_signup": True,
                "is_test_mode": is_test_mode,
            },
        )
        self.db.add(tx)
        await self.db.commit()

        key_id = settings.RAZORPAY_KEY_ID if self.is_configured() else "rzp_test_simulated_key"

        return RazorpayOrderResponse(
            order_id=order_id,
            amount_paise=amount_paise,
            currency=currency,
            key_id=key_id,
            company_name=company_name,
            admin_email=email.lower(),
            plan_name=plan.name,
            extend_days=extend_days,
            is_test_mode=is_test_mode,
        )

    async def create_order(
        self,
        company: CompanyTenant,
        plan_id: str,
        extend_days: int = 30,
    ) -> RazorpayOrderResponse:
        """Create a Razorpay order server-side and record a PaymentTransaction."""
        res_plan = await self.db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        plan = res_plan.scalar_one_or_none()
        if not plan:
            raise NotFoundError("SubscriptionPlan", plan_id)

        amount_paise = calculate_amount_paise(plan, extend_days)
        currency = settings.RAZORPAY_CURRENCY or "INR"

        order_id = f"order_sim_{uuid.uuid4().hex[:16]}"
        is_test_mode = not self.is_configured()

        if not is_test_mode:
            # Call real Razorpay Orders API
            auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            payload = {
                "amount": amount_paise,
                "currency": currency,
                "receipt": f"rcpt_{company.slug[:10]}_{uuid.uuid4().hex[:8]}",
                "notes": {
                    "company_id": company.id,
                    "company_slug": company.slug,
                    "plan_id": plan.id,
                    "extend_days": str(extend_days),
                    "admin_email": company.admin_email,
                },
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post("https://api.razorpay.com/v1/orders", auth=auth, json=payload)
                if resp.status_code != 200:
                    logger.error(f"Razorpay order creation failed: {resp.text}")
                    raise ValidationError(f"Gateway error creating payment order: {resp.text}")
                order_data = resp.json()
                order_id = order_data["id"]
        else:
            logger.info(f"[RAZORPAY SIMULATION MODE] Created order {order_id} for company {company.company_name}")

        # Record payment transaction
        tx = PaymentTransaction(
            company_tenant_id=company.id,
            razorpay_order_id=order_id,
            amount_paise=amount_paise,
            currency=currency,
            status="CREATED",
            plan_id=plan.id,
            extend_days=extend_days,
            details={
                "company_name": company.company_name,
                "plan_name": plan.name,
                "is_test_mode": is_test_mode,
            },
        )
        self.db.add(tx)
        await self.db.commit()

        key_id = settings.RAZORPAY_KEY_ID if self.is_configured() else "rzp_test_simulated_key"

        return RazorpayOrderResponse(
            order_id=order_id,
            amount_paise=amount_paise,
            currency=currency,
            key_id=key_id,
            company_name=company.company_name,
            admin_email=company.admin_email,
            plan_name=plan.name,
            extend_days=extend_days,
            is_test_mode=is_test_mode,
        )

    async def verify_payment(
        self,
        company: CompanyTenant,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> RazorpayVerifyPaymentResponse:
        """Verify client-side Razorpay signature and instantly unfreeze/extend company workspace."""
        res_tx = await self.db.execute(
            select(PaymentTransaction).where(PaymentTransaction.razorpay_order_id == order_id)
        )
        tx = res_tx.scalar_one_or_none()
        if not tx:
            raise NotFoundError("PaymentTransaction", order_id)

        # Signature verification
        is_simulated = order_id.startswith("order_sim_") or not self.is_configured()
        if not is_simulated:
            expected_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
                f"{order_id}|{payment_id}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_signature, signature):
                tx.status = "FAILED"
                tx.failure_reason = "Signature verification mismatch"
                await self.db.commit()
                raise ValidationError("Payment signature verification failed. Tampered or invalid callback.")

        # Update transaction
        tx.status = "CAPTURED"
        tx.razorpay_payment_id = payment_id
        tx.razorpay_signature = signature

        # Unfreeze and extend company workspace
        now = datetime.now(timezone.utc)
        current_exp = company.subscription_expires_at
        if current_exp.tzinfo is None:
            current_exp = current_exp.replace(tzinfo=timezone.utc)

        base_date = max(now, current_exp)
        company.subscription_expires_at = base_date + timedelta(days=tx.extend_days)
        company.subscription_status = "ACTIVE"
        company.is_blocked = False
        company.blocked_reason = None
        if tx.plan_id:
            company.plan_id = tx.plan_id

        # Audit log in master DB
        self.db.add(
            AuditLog(
                action="PAYMENT_CAPTURED_UNFREEZE",
                resource_type="COMPANY_TENANT",
                resource_id=company.slug,
                details={
                    "company_name": company.company_name,
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "plan_id": company.plan_id,
                    "new_expires_at": company.subscription_expires_at.isoformat(),
                },
            )
        )

        await self.db.commit()
        await self.db.refresh(company)

        # Send themed activation email
        exp_formatted = company.subscription_expires_at.strftime("%b %d, %Y")
        amount_str = f"₹{tx.amount_paise / 100:.2f}"
        await self.email_service.send_subscription_activated_email(
            recipient=company.admin_email,
            company_name=company.company_name,
            plan_name="Pro Studio" if company.plan_id == "pro_studio" else "Starter Studio",
            expires_at_str=exp_formatted,
            amount_str=amount_str,
        )

        logger.info(f"Payment verified for {company.company_name}. Workspace unblocked until {company.subscription_expires_at}")

        return RazorpayVerifyPaymentResponse(
            success=True,
            message="Payment successfully verified! Workspace has been unblocked.",
            company_name=company.company_name,
            subscription_status=company.subscription_status,
            subscription_expires_at=company.subscription_expires_at,
            plan_id=company.plan_id,
        )

    async def list_transactions(self, company_tenant_id: str) -> List[PaymentTransactionOut]:
        """Fetch all payment transactions and receipts for a company tenant."""
        res = await self.db.execute(
            select(PaymentTransaction, SubscriptionPlan.name.label("plan_title"))
            .outerjoin(SubscriptionPlan, PaymentTransaction.plan_id == SubscriptionPlan.id)
            .where(PaymentTransaction.company_tenant_id == company_tenant_id)
            .order_by(PaymentTransaction.created_at.desc())
        )
        rows = res.all()
        result = []
        for tx, plan_title in rows:
            amount_val = tx.amount_paise / 100.0
            formatted = f"₹{amount_val:,.2f}" if tx.currency == "INR" else f"${amount_val:,.2f}"
            plan_label = plan_title or (tx.details.get("plan_name") if tx.details else None) or ("Pro Studio" if tx.plan_id == "pro_studio" else "Starter Studio")
            result.append(
                PaymentTransactionOut(
                    id=tx.id,
                    company_tenant_id=tx.company_tenant_id,
                    razorpay_order_id=tx.razorpay_order_id,
                    razorpay_payment_id=tx.razorpay_payment_id,
                    amount_paise=tx.amount_paise,
                    amount_formatted=formatted,
                    currency=tx.currency,
                    status=tx.status,
                    plan_id=tx.plan_id,
                    plan_name=plan_label,
                    extend_days=tx.extend_days,
                    created_at=tx.created_at,
                    receipt_url=f"/api/v1/payments/receipt/{tx.id}",
                )
            )
        return result

    async def generate_receipt_html(
        self,
        transaction_id: str,
        user_company: Optional[CompanyTenant] = None,
    ) -> str:
        """Generate a production-grade printable HTML tax invoice & receipt for a transaction."""
        res = await self.db.execute(
            select(PaymentTransaction, CompanyTenant, SubscriptionPlan)
            .outerjoin(CompanyTenant, PaymentTransaction.company_tenant_id == CompanyTenant.id)
            .outerjoin(SubscriptionPlan, PaymentTransaction.plan_id == SubscriptionPlan.id)
            .where(PaymentTransaction.id == transaction_id)
        )
        row = res.first()
        if not row:
            raise NotFoundError("PaymentTransaction", transaction_id)
        tx, company, plan = row

        if user_company and tx.company_tenant_id and tx.company_tenant_id != user_company.id:
            raise UnauthorizedError("Unauthorized to view this receipt.")

        company_name = (
            company.company_name
            if company
            else (tx.details.get("company_name", "BlogPilot Studio Tenant") if tx.details else "BlogPilot Studio")
        )
        admin_email = (
            company.admin_email
            if company
            else (tx.details.get("admin_email", "admin@studio.local") if tx.details else "N/A")
        )
        plan_name = (
            plan.name
            if plan
            else (tx.details.get("plan_name", "Studio Plan") if tx.details else ("Pro Studio" if tx.plan_id == "pro_studio" else "Starter Studio"))
        )
        amount_val = tx.amount_paise / 100.0
        formatted_amount = f"₹{amount_val:,.2f}" if tx.currency == "INR" else f"${amount_val:,.2f}"
        date_str = tx.created_at.strftime("%B %d, %Y, %I:%M %p UTC")
        receipt_num = f"INV-{tx.id[:8].upper()}"
        payment_id_display = tx.razorpay_payment_id or "Simulated Gateway Payment"
        order_id_display = tx.razorpay_order_id or "N/A"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Payment Receipt - {receipt_num} - BlogPilot</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: #f8fafc;
      color: #0f172a;
      margin: 0;
      padding: 40px 20px;
    }}
    .invoice-card {{
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.05);
      overflow: hidden;
    }}
    .header {{
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      padding: 32px 36px;
      color: #ffffff;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .header h1 {{
      margin: 0;
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }}
    .header p {{
      margin: 4px 0 0 0;
      font-size: 13px;
      opacity: 0.92;
    }}
    .badge-paid {{
      background: #10b981;
      color: #ffffff;
      padding: 6px 16px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .content {{
      padding: 36px 36px;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 32px;
      padding-bottom: 24px;
      border-bottom: 1px solid #e2e8f0;
    }}
    .meta-col strong {{
      display: block;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #64748b;
      margin-bottom: 6px;
    }}
    .meta-col span {{
      font-size: 14px;
      font-weight: 600;
      color: #1e293b;
    }}
    .items-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 28px;
    }}
    .items-table th {{
      text-align: left;
      font-size: 12px;
      text-transform: uppercase;
      color: #64748b;
      padding: 10px 0;
      border-bottom: 2px solid #e2e8f0;
    }}
    .items-table td {{
      padding: 16px 0;
      border-bottom: 1px solid #f1f5f9;
      font-size: 14px;
    }}
    .total-row {{
      display: flex;
      justify-content: flex-end;
      align-items: baseline;
      gap: 16px;
      padding-top: 12px;
      font-size: 16px;
    }}
    .total-row strong {{
      font-size: 26px;
      color: #4f46e5;
    }}
    .actions {{
      background: #f8fafc;
      padding: 20px 36px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .btn-print {{
      background: #4f46e5;
      color: #ffffff;
      border: none;
      padding: 10px 24px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 14px;
      cursor: pointer;
      transition: background 0.15s ease;
    }}
    .btn-print:hover {{
      background: #4338ca;
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .invoice-card {{
        border: none;
        box-shadow: none;
      }}
      .actions {{
        display: none;
      }}
    }}
  </style>
</head>
<body>
  <div class="invoice-card">
    <div class="header">
      <div>
        <h1>BlogPilot Studio</h1>
        <p>Official Payment Receipt & Tax Invoice</p>
      </div>
      <span class="badge-paid">{tx.status}</span>
    </div>

    <div class="content">
      <div class="meta-grid">
        <div class="meta-col">
          <strong>Receipt Number</strong>
          <span>{receipt_num}</span>
        </div>
        <div class="meta-col">
          <strong>Date & Time</strong>
          <span>{date_str}</span>
        </div>
        <div class="meta-col">
          <strong>Billed To</strong>
          <span>{company_name}</span>
          <div style="font-size: 12px; color: #64748b; margin-top: 2px;">{admin_email}</div>
        </div>
        <div class="meta-col">
          <strong>Payment Reference</strong>
          <span>{payment_id_display}</span>
          <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">Order ID: {order_id_display}</div>
        </div>
      </div>

      <table class="items-table">
        <thead>
          <tr>
            <th>Description</th>
            <th style="text-align: center;">Validity</th>
            <th style="text-align: right;">Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <strong>{plan_name} Subscription</strong>
              <div style="font-size: 12px; color: #64748b; margin-top: 2px;">
                AI Studio Content Generation Suite & Autonomous Publishing Workspace.
              </div>
            </td>
            <td style="text-align: center;">+{tx.extend_days} Days</td>
            <td style="text-align: right; font-weight: 700;">{formatted_amount}</td>
          </tr>
        </tbody>
      </table>

      <div class="total-row">
        <span>Total Paid ({tx.currency}):</span>
        <strong>{formatted_amount}</strong>
      </div>
    </div>

    <div class="actions">
      <span style="font-size: 12px; color: #64748b;">This is an electronically generated receipt for your workspace subscription.</span>
      <button onclick="window.print()" class="btn-print">🖨️ Print / Save as PDF</button>
    </div>
  </div>
</body>
</html>"""

    async def process_webhook(
        self,
        raw_body: bytes,
        signature_header: Optional[str],
    ) -> Dict[str, Any]:
        """
        Process Razorpay webhook events with strict signature verification & idempotency.
        Unfreezes on payment.captured / subscription.charged, and freezes on subscription.halted / payment.failed.
        """
        # 1. Verify Webhook Signature if secret configured
        if settings.RAZORPAY_WEBHOOK_SECRET and settings.RAZORPAY_WEBHOOK_SECRET != "YOUR_RAZORPAY_WEBHOOK_SECRET":
            if not signature_header:
                raise UnauthorizedError("Missing X-Razorpay-Signature header.")
            expected_sig = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, signature_header):
                logger.error("Razorpay webhook signature mismatch.")
                raise UnauthorizedError("Invalid Razorpay webhook signature.")

        # 2. Parse payload
        try:
            event = json.loads(raw_body.decode("utf-8"))
        except Exception as err:
            raise ValidationError(f"Invalid JSON webhook payload: {err}")

        event_id = event.get("event_id") or event.get("id") or f"ev_{uuid.uuid4().hex[:12]}"
        event_name = event.get("event")

        logger.info(f"Received Razorpay Webhook: {event_name} (ID: {event_id})")

        # 3. Idempotency Guard: prevent duplicate execution
        res_dup = await self.db.execute(
            select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.id == event_id)
        )
        if res_dup.scalar_one_or_none():
            logger.info(f"Webhook event {event_id} already processed. Skipping duplicate.")
            return {"status": "already_processed", "event_id": event_id}

        # Save event
        record = ProcessedWebhookEvent(
            id=event_id,
            event_type=event_name or "unknown",
            status="PROCESSED",
            payload=event,
        )
        self.db.add(record)

        # 4. Dispatch Event
        payload_data = event.get("payload", {})

        if event_name in {"payment.captured", "order.paid"}:
            await self._handle_payment_captured(payload_data)
        elif event_name == "payment.failed":
            await self._handle_payment_failed(payload_data)
        elif event_name in {"subscription.halted", "subscription.cancelled"}:
            await self._handle_subscription_halted(payload_data, reason=f"Gateway event: {event_name}")
        elif event_name in {"subscription.charged", "subscription.activated"}:
            await self._handle_subscription_charged(payload_data)

        await self.db.commit()
        return {"status": "success", "event_id": event_id, "event": event_name}

    async def _handle_payment_captured(self, payload_data: Dict[str, Any]) -> None:
        payment = payload_data.get("payment", {}).get("entity", {})
        order_id = payment.get("order_id")
        notes = payment.get("notes", {})
        company_id = notes.get("company_id")
        company_slug = notes.get("company_slug")

        tx = None
        if order_id:
            res_tx = await self.db.execute(select(PaymentTransaction).where(PaymentTransaction.razorpay_order_id == order_id))
            tx = res_tx.scalar_one_or_none()

        company = None
        if tx:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.id == tx.company_tenant_id))
            company = res_c.scalar_one_or_none()
        elif company_id:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
            company = res_c.scalar_one_or_none()
        elif company_slug:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.slug == company_slug))
            company = res_c.scalar_one_or_none()

        if not company:
            logger.warning("Could not find matching CompanyTenant for captured payment.")
            return

        # UNFREEZE company & extend subscription
        extend_days = tx.extend_days if tx else 30
        now = datetime.now(timezone.utc)
        current_exp = company.subscription_expires_at
        if current_exp.tzinfo is None:
            current_exp = current_exp.replace(tzinfo=timezone.utc)

        base_date = max(now, current_exp)
        company.subscription_expires_at = base_date + timedelta(days=extend_days)
        company.subscription_status = "ACTIVE"
        company.is_blocked = False
        company.blocked_reason = None
        if tx and tx.plan_id:
            company.plan_id = tx.plan_id

        if tx:
            tx.status = "CAPTURED"
            tx.razorpay_payment_id = payment.get("id")

        self.db.add(
            AuditLog(
                action="WEBHOOK_PAYMENT_CAPTURED_UNFREEZE",
                resource_type="COMPANY_TENANT",
                resource_id=company.slug,
                details={"company_name": company.company_name, "order_id": order_id, "payment_id": payment.get("id")},
            )
        )

        exp_str = company.subscription_expires_at.strftime("%b %d, %Y")
        amount = payment.get("amount", 0) / 100
        await self.email_service.send_subscription_activated_email(
            recipient=company.admin_email,
            company_name=company.company_name,
            plan_name=company.plan_id,
            expires_at_str=exp_str,
            amount_str=f"₹{amount:.2f}",
        )
        logger.info(f"Webhook unblocked company {company.company_name} until {company.subscription_expires_at}")

    async def _handle_payment_failed(self, payload_data: Dict[str, Any]) -> None:
        payment = payload_data.get("payment", {}).get("entity", {})
        order_id = payment.get("order_id")
        error_desc = payment.get("error_description") or "Payment processing failed"

        if order_id:
            res_tx = await self.db.execute(select(PaymentTransaction).where(PaymentTransaction.razorpay_order_id == order_id))
            tx = res_tx.scalar_one_or_none()
            if tx:
                tx.status = "FAILED"
                tx.failure_reason = error_desc
                res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.id == tx.company_tenant_id))
                company = res_c.scalar_one_or_none()
                if company:
                    await self.email_service.send_payment_failed_email(
                        recipient=company.admin_email,
                        company_name=company.company_name,
                        failure_reason=error_desc,
                    )
        logger.warning(f"Webhook recorded payment failure: {error_desc}")

    async def _handle_subscription_halted(self, payload_data: Dict[str, Any], reason: str) -> None:
        sub = payload_data.get("subscription", {}).get("entity", {})
        notes = sub.get("notes", {})
        company_id = notes.get("company_id")
        company_slug = notes.get("company_slug")

        company = None
        if company_id:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
            company = res_c.scalar_one_or_none()
        elif company_slug:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.slug == company_slug))
            company = res_c.scalar_one_or_none()

        if company:
            # FREEZE company
            company.is_blocked = True
            company.subscription_status = "BLOCKED"
            company.blocked_reason = reason
            self.db.add(
                AuditLog(
                    action="WEBHOOK_SUBSCRIPTION_HALTED_FREEZE",
                    resource_type="COMPANY_TENANT",
                    resource_id=company.slug,
                    details={"reason": reason},
                )
            )
            await self.email_service.send_workspace_frozen_email(
                recipient=company.admin_email,
                company_name=company.company_name,
                reason=reason,
            )
            logger.warning(f"Webhook FROZE company {company.company_name}: {reason}")

    async def _handle_subscription_charged(self, payload_data: Dict[str, Any]) -> None:
        sub = payload_data.get("subscription", {}).get("entity", {})
        notes = sub.get("notes", {})
        company_id = notes.get("company_id")
        company_slug = notes.get("company_slug")

        company = None
        if company_id:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
            company = res_c.scalar_one_or_none()
        elif company_slug:
            res_c = await self.db.execute(select(CompanyTenant).where(CompanyTenant.slug == company_slug))
            company = res_c.scalar_one_or_none()

        if company:
            now = datetime.now(timezone.utc)
            current_exp = company.subscription_expires_at
            if current_exp.tzinfo is None:
                current_exp = current_exp.replace(tzinfo=timezone.utc)

            base_date = max(now, current_exp)
            company.subscription_expires_at = base_date + timedelta(days=30)
            company.subscription_status = "ACTIVE"
            company.is_blocked = False
            company.blocked_reason = None
            self.db.add(
                AuditLog(
                    action="WEBHOOK_SUBSCRIPTION_CHARGED_UNFREEZE",
                    resource_type="COMPANY_TENANT",
                    resource_id=company.slug,
                    details={"new_expires_at": company.subscription_expires_at.isoformat()},
                )
            )
            exp_str = company.subscription_expires_at.strftime("%b %d, %Y")
            await self.email_service.send_subscription_activated_email(
                recipient=company.admin_email,
                company_name=company.company_name,
                plan_name=company.plan_id,
                expires_at_str=exp_str,
            )
            logger.info(f"Webhook charged and renewed subscription for {company.company_name}")
