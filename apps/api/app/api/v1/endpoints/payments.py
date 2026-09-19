"""Endpoints for Razorpay payments, signature verification, and automated webhook lifecycle."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_master_db
from app.models.entities import CompanyTenant, User
from app.schemas.schemas import (
    PaymentTransactionOut,
    RazorpayCreateOrderRequest,
    RazorpayCreateSignupOrderRequest,
    RazorpayOrderResponse,
    RazorpayVerifyPaymentRequest,
    RazorpayVerifyPaymentResponse,
)
from app.services.auth_service import get_current_user
from app.services.razorpay_service import RazorpayService

router = APIRouter()


@router.get("/razorpay/config")
async def get_razorpay_config():
    """Returns Razorpay public key and currency configuration."""
    is_configured = bool(
        settings.RAZORPAY_KEY_ID
        and settings.RAZORPAY_KEY_SECRET
        and not settings.RAZORPAY_KEY_ID.startswith("YOUR_")
        and not settings.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder")
    )
    return {
        "key_id": settings.RAZORPAY_KEY_ID if is_configured else "rzp_test_simulated_key",
        "currency": settings.RAZORPAY_CURRENCY or "INR",
        "is_configured": is_configured,
    }


@router.post("/razorpay/create-signup-order", response_model=RazorpayOrderResponse)
async def create_razorpay_signup_order(
    req: RazorpayCreateSignupOrderRequest,
    db: AsyncSession = Depends(get_master_db),
):
    """Public endpoint: creates a Razorpay order before company registration."""
    service = RazorpayService(db)
    return await service.create_signup_order(
        company_name=req.company_name,
        email=req.email,
        plan_id=req.plan_id,
    )


@router.post("/razorpay/create-order", response_model=RazorpayOrderResponse)
async def create_razorpay_order(
    req: RazorpayCreateOrderRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_master_db),
):
    """Authenticated tenant admin generates a Razorpay order for plan extension/upgrade."""
    company_tenant = getattr(request.state, "company_tenant", None)
    if not company_tenant:
        raise NotFoundError("CompanyTenant", "Authenticated user does not belong to a company tenant.")

    # Refresh tenant record from master DB
    res_c = await db.execute(select(CompanyTenant).where(CompanyTenant.id == company_tenant.id))
    company = res_c.scalar_one_or_none()
    if not company:
        raise NotFoundError("CompanyTenant", company_tenant.id)

    service = RazorpayService(db)
    return await service.create_order(
        company=company,
        plan_id=req.plan_id,
        extend_days=req.extend_days,
    )


@router.post("/razorpay/verify-payment", response_model=RazorpayVerifyPaymentResponse)
async def verify_razorpay_payment(
    req: RazorpayVerifyPaymentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_master_db),
):
    """Verifies client-side signature returned by Razorpay Checkout modal."""
    company_tenant = getattr(request.state, "company_tenant", None)
    if not company_tenant:
        raise NotFoundError("CompanyTenant", "Authenticated user does not belong to a company tenant.")

    res_c = await db.execute(select(CompanyTenant).where(CompanyTenant.id == company_tenant.id))
    company = res_c.scalar_one_or_none()
    if not company:
        raise NotFoundError("CompanyTenant", company_tenant.id)

    service = RazorpayService(db)
    return await service.verify_payment(
        company=company,
        order_id=req.razorpay_order_id,
        payment_id=req.razorpay_payment_id,
        signature=req.razorpay_signature,
    )


@router.post("/razorpay/webhook", status_code=status.HTTP_200_OK)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: AsyncSession = Depends(get_master_db),
) -> Dict[str, Any]:
    """
    Public Razorpay Webhook endpoint.
    Verifies HMAC SHA-256 signature on raw request body, executes idempotent state transitions,
    and automatically unfreezes (payment.captured) or freezes (subscription.halted) company tenants.
    """
    raw_body = await request.body()
    service = RazorpayService(db)
    return await service.process_webhook(
        raw_body=raw_body,
        signature_header=x_razorpay_signature,
    )


@router.get("/transactions/my", response_model=List[PaymentTransactionOut])
async def list_my_transactions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_master_db),
):
    """Fetch payment transactions and invoices for the authenticated studio workspace."""
    company_tenant = getattr(request.state, "company_tenant", None)
    if not company_tenant:
        return []

    service = RazorpayService(db)
    return await service.list_transactions(company_tenant_id=company_tenant.id)


@router.get("/receipt/{transaction_id}")
async def get_transaction_receipt(
    transaction_id: str,
    request: Request,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_master_db),
):
    """
    Render and download a printable HTML tax receipt & payment invoice.
    Can authenticate via standard cookies/headers or query token.
    """
    company_tenant = getattr(request.state, "company_tenant", None)
    if not company_tenant and token:
        payload = decode_access_token(token)
        if payload and payload.get("company_id"):
            res_c = await db.execute(select(CompanyTenant).where(CompanyTenant.id == payload["company_id"]))
            company_tenant = res_c.scalar_one_or_none()

    service = RazorpayService(db)
    html_content = await service.generate_receipt_html(
        transaction_id=transaction_id,
        user_company=company_tenant,
    )
    return Response(content=html_content, media_type="text/html")
