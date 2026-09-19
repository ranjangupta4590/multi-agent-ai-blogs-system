"""Company tenant service managing multi-database provisioning, plans, and freeze lifecycle."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.logging import logger
from app.core.security import create_access_token, verify_password
from app.db.tenant_manager import create_company_database, get_company_engine, seed_company_database
from app.models.entities import AuditLog, CompanyTenant, PaymentTransaction, SubscriptionPlan, User
from app.schemas.schemas import (
    CompanyRenewRequest,
    CompanySelfRenewRequest,
    CompanyTenantOut,
    StudioSignupRequest,
    SubscriptionPlanOut,
    SubscriptionPlanUpdate,
    TokenResponse,
)
from sqlalchemy.ext.asyncio import async_sessionmaker


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")[:60]


class CompanyService:
    def __init__(self, master_db: AsyncSession):
        self.master_db = master_db

    async def list_plans(self) -> List[SubscriptionPlan]:
        res = await self.master_db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.is_active == True).order_by(SubscriptionPlan.price_monthly_usd.asc())
        )
        return list(res.scalars().all())

    async def update_plan(self, plan_id: str, req: SubscriptionPlanUpdate) -> SubscriptionPlan:
        res = await self.master_db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        plan = res.scalar_one_or_none()
        if not plan:
            raise NotFoundError("SubscriptionPlan", plan_id)

        if req.price_monthly_usd is not None:
            plan.price_monthly_usd = float(req.price_monthly_usd)
        if req.name is not None:
            plan.name = req.name
        if req.description is not None:
            plan.description = req.description
        if req.ai_provider_included is not None:
            plan.ai_provider_included = req.ai_provider_included
        if req.max_articles_monthly is not None:
            plan.max_articles_monthly = req.max_articles_monthly
        if req.has_fact_checking is not None:
            plan.has_fact_checking = req.has_fact_checking
        if req.has_wordpress_syndication is not None:
            plan.has_wordpress_syndication = req.has_wordpress_syndication
        if req.has_advanced_seo is not None:
            plan.has_advanced_seo = req.has_advanced_seo

        await self.master_db.commit()
        await self.master_db.refresh(plan)
        return plan

    async def studio_signup(self, req: StudioSignupRequest, ip_address: Optional[str] = None) -> TokenResponse:
        """Provision dedicated company database and register studio admin."""
        company_slug = slugify(req.company_name)
        if not company_slug:
            raise ValidationError("A valid company name is required.")

        # Check existing company by slug or admin email in Master DB
        existing_res = await self.master_db.execute(
            select(CompanyTenant).where(
                (CompanyTenant.slug == company_slug) | (CompanyTenant.admin_email == req.email.lower())
            )
        )
        if existing_res.scalar_one_or_none():
            raise ConflictError("A company with this name or admin email already exists.")

        # Verify plan exists
        plan_res = await self.master_db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == req.plan_id)
        )
        plan = plan_res.scalar_one_or_none()
        if not plan:
            req.plan_id = "starter_studio"

        # Verify Razorpay signature if payment details provided
        tx: Optional[PaymentTransaction] = None
        if req.razorpay_order_id:
            from app.services.razorpay_service import RazorpayService
            res_tx = await self.master_db.execute(
                select(PaymentTransaction).where(PaymentTransaction.razorpay_order_id == req.razorpay_order_id)
            )
            tx = res_tx.scalar_one_or_none()
            if tx:
                razorpay_svc = RazorpayService(self.master_db)
                is_valid = razorpay_svc.verify_signature(
                    order_id=req.razorpay_order_id,
                    payment_id=req.razorpay_payment_id or "",
                    signature=req.razorpay_signature or "",
                )
                if not is_valid:
                    tx.status = "FAILED"
                    tx.failure_reason = "Payment signature mismatch during signup"
                    await self.master_db.commit()
                    raise ValidationError("Payment signature verification failed. Please try again.")

        # 1. Provision dedicated database (PostgreSQL CREATE DATABASE or SQLite file)
        db_name, company_db_url = await create_company_database(company_slug)

        # 2. Seed Admin & initial organization inside the dedicated database
        company_admin = await seed_company_database(
            company_db_url=company_db_url,
            company_name=req.company_name,
            company_slug=company_slug,
            admin_full_name=req.full_name,
            admin_email=req.email.lower(),
            admin_password=req.password,
        )

        # 3. Save company record in Master DB with 30-day initial subscription
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)

        tenant = CompanyTenant(
            company_name=req.company_name,
            slug=company_slug,
            admin_email=req.email.lower(),
            db_name=db_name,
            db_connection_url=company_db_url,
            plan_id=req.plan_id,
            subscription_status="ACTIVE",
            subscription_expires_at=expires_at,
            is_blocked=False,
        )
        self.master_db.add(tenant)

        audit = AuditLog(
            action="STUDIO_COMPANY_CREATED",
            resource_type="COMPANY_TENANT",
            resource_id=company_slug,
            details={
                "company_name": req.company_name,
                "admin_email": req.email.lower(),
                "db_name": db_name,
                "plan_id": req.plan_id,
                "has_razorpay_payment": bool(tx and req.razorpay_payment_id),
            },
            ip_address=ip_address,
        )
        self.master_db.add(audit)
        await self.master_db.commit()
        await self.master_db.refresh(tenant)

        # Link payment transaction to new company tenant
        if tx:
            tx.company_tenant_id = tenant.id
            tx.status = "CAPTURED"
            tx.razorpay_payment_id = req.razorpay_payment_id
            tx.razorpay_signature = req.razorpay_signature
            tx.details = {
                **(tx.details or {}),
                "company_id": tenant.id,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.master_db.commit()

            # Dispatch styled activation email with payment confirmation
            try:
                from app.services.email_service import EmailService
                email_svc = EmailService()
                await email_svc.send_subscription_activated_email(
                    recipient=tenant.admin_email,
                    company_name=tenant.company_name,
                    plan_name="Pro Studio" if tenant.plan_id == "pro_studio" else "Starter Studio",
                    expires_at_str=tenant.subscription_expires_at.strftime("%b %d, %Y"),
                    amount_str=f"₹{tx.amount_paise / 100:.2f}",
                )
            except Exception as e:
                logger.warning(f"Could not send signup payment confirmation email: {e}")
        else:
            # Create setup trial transaction record so billing history is never blank
            plan_record = await self.master_db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == req.plan_id))
            p_obj = plan_record.scalar_one_or_none()
            p_name = p_obj.name if p_obj else ("Pro Studio" if req.plan_id == "pro_studio" else "Starter Studio")
            trial_tx = PaymentTransaction(
                company_tenant_id=tenant.id,
                razorpay_order_id=f"order_init_{uuid.uuid4().hex[:12]}",
                razorpay_payment_id=f"pay_init_{uuid.uuid4().hex[:12]}",
                amount_paise=0,
                currency="INR",
                status="CAPTURED",
                plan_id=req.plan_id,
                extend_days=30,
                details={
                    "company_name": tenant.company_name,
                    "plan_name": p_name,
                    "note": "Complimentary Studio Allocation",
                },
            )
            self.master_db.add(trial_tx)
            await self.master_db.commit()

        # 4. Generate JWT with tenant database routing claims
        token = create_access_token(
            subject=company_admin.id,
            claims={
                "email": company_admin.email,
                "role": company_admin.role,
                "org_id": company_slug,
                "company_id": tenant.id,
                "company_slug": tenant.slug,
                "tenant_db_url": tenant.db_connection_url,
            },
        )

        return TokenResponse(
            access_token=token,
            user_id=company_admin.id,
            email=company_admin.email,
            full_name=company_admin.full_name,
            role=company_admin.role,
            organization_id=company_slug,
        )

    async def list_companies(self) -> List[CompanyTenant]:
        res = await self.master_db.execute(select(CompanyTenant).order_by(CompanyTenant.created_at.desc()))
        return list(res.scalars().all())

    async def freeze_company(self, company_id: str, reason: str = "Frozen by Superadmin") -> CompanyTenant:
        res = await self.master_db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
        tenant = res.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("CompanyTenant", company_id)

        tenant.is_blocked = True
        tenant.blocked_reason = reason
        tenant.subscription_status = "BLOCKED"
        await self.master_db.commit()
        await self.master_db.refresh(tenant)
        logger.warning(f"Company {tenant.company_name} ({tenant.db_name}) has been FROZEN.")
        return tenant

    async def unfreeze_company(self, company_id: str) -> CompanyTenant:
        res = await self.master_db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
        tenant = res.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("CompanyTenant", company_id)

        tenant.is_blocked = False
        tenant.blocked_reason = None
        
        now = datetime.now(timezone.utc)
        expires_at = tenant.subscription_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        tenant.subscription_status = "ACTIVE" if now <= expires_at else "EXPIRED"
        await self.master_db.commit()
        await self.master_db.refresh(tenant)
        logger.info(f"Company {tenant.company_name} ({tenant.db_name}) has been UNFROZEN.")
        return tenant

    async def renew_company_subscription(self, company_id: str, req: CompanyRenewRequest) -> CompanyTenant:
        res = await self.master_db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
        tenant = res.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("CompanyTenant", company_id)

        now = datetime.now(timezone.utc)
        current_exp = tenant.subscription_expires_at
        if current_exp.tzinfo is None:
            current_exp = current_exp.replace(tzinfo=timezone.utc)

        base_date = max(now, current_exp)
        tenant.subscription_expires_at = base_date + timedelta(days=req.extend_days)
        tenant.subscription_status = "ACTIVE"
        tenant.is_blocked = False
        tenant.blocked_reason = None
        if req.plan_id:
            tenant.plan_id = req.plan_id

        await self.master_db.commit()
        await self.master_db.refresh(tenant)
        logger.info(f"Company {tenant.company_name} renewed until {tenant.subscription_expires_at}")
        return tenant

    async def renew_company_by_credentials(
        self, email: str, password: str, extend_days: int = 30, new_plan_id: Optional[str] = None
    ) -> CompanyTenant:
        res = await self.master_db.execute(
            select(CompanyTenant).where(CompanyTenant.admin_email == email.lower())
        )
        tenant = res.scalar_one_or_none()
        if not tenant:
            raise NotFoundError("CompanyTenant", email)

        tenant_engine = get_company_engine(tenant.db_connection_url)
        factory = async_sessionmaker(bind=tenant_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as tenant_session:
            user_res = await tenant_session.execute(
                select(User).where(User.email == email.lower())
            )
            admin_user = user_res.scalar_one_or_none()
            if not admin_user or not verify_password(password, admin_user.hashed_password):
                raise UnauthorizedError("Invalid email or password for renewal.")

        now = datetime.now(timezone.utc)
        current_exp = tenant.subscription_expires_at
        if current_exp.tzinfo is None:
            current_exp = current_exp.replace(tzinfo=timezone.utc)

        base_date = max(now, current_exp)
        tenant.subscription_expires_at = base_date + timedelta(days=extend_days)
        tenant.subscription_status = "ACTIVE"
        tenant.is_blocked = False
        tenant.blocked_reason = None
        if new_plan_id:
            tenant.plan_id = new_plan_id

        await self.master_db.commit()
        await self.master_db.refresh(tenant)
        logger.info(f"Self-renewed company {tenant.company_name} for {extend_days} days (plan: {tenant.plan_id}).")
        return tenant
