"""Superadmin endpoints for managing company databases, freeze controls, and subscription plans."""
from typing import List
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ForbiddenError, NotFoundError
from app.core.rbac import Permission
from app.db.session import get_db, get_master_db
from app.models.entities import CompanyTenant, User
from app.schemas.schemas import (
    CompanyFreezeRequest,
    CompanyRenewRequest,
    CompanySelfRenewRequest,
    CompanyTenantOut,
    StudioSignupRequest,
    SubscriptionPlanOut,
    SubscriptionPlanUpdate,
    TokenResponse,
)
from app.services.auth_service import get_current_user, require_permission
from app.services.company_service import CompanyService

router = APIRouter()


# --- PUBLIC & STUDIO ENDPOINTS ---

@router.get("/plans", response_model=List[SubscriptionPlanOut])
async def list_public_plans(db: AsyncSession = Depends(get_master_db)):
    """List all available studio subscription plans and current prices."""
    service = CompanyService(db)
    return await service.list_plans()


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def studio_signup(
    req: StudioSignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_master_db),
):
    """Provision a dedicated database for a company and create its Studio Admin."""
    client_ip = request.client.host if request.client else "unknown"
    service = CompanyService(db)
    token_resp = await service.studio_signup(req, ip_address=client_ip)

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token_resp.access_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite=settings.SAME_SITE_POLICY,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return token_resp


@router.post("/renew-by-credentials", response_model=CompanyTenantOut)
async def renew_by_credentials(
    req: CompanySelfRenewRequest,
    db: AsyncSession = Depends(get_master_db),
):
    """Allows a company admin to renew their expired subscription using their account credentials."""
    service = CompanyService(db)
    return await service.renew_company_by_credentials(
        email=req.email,
        password=req.password,
        extend_days=req.extend_days,
        new_plan_id=req.plan_id,
    )


# --- TENANT SELF-SERVICE ENDPOINTS ---

@router.get("/my-subscription", response_model=CompanyTenantOut)
async def get_my_subscription(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_master_db),
):
    """Allows an authenticated tenant admin to view their own company's subscription and database details."""
    company_tenant = getattr(request.state, "company_tenant", None)
    if not company_tenant:
        raise NotFoundError("CompanyTenant", "User does not belong to a company tenant.")
    
    res = await db.execute(select(CompanyTenant).where(CompanyTenant.id == company_tenant.id))
    company = res.scalar_one_or_none()
    if not company:
        raise NotFoundError("CompanyTenant", company_tenant.id)
    return company


@router.post("/renew-my-subscription", response_model=CompanyTenantOut)
async def renew_my_subscription(
    req: CompanySelfRenewRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_master_db),
):
    """Allows an authenticated tenant admin to renew or switch plan for their company."""
    company_tenant = getattr(request.state, "company_tenant", None)
    if not company_tenant:
        raise NotFoundError("CompanyTenant", "User does not belong to a company tenant.")
    service = CompanyService(db)
    return await service.renew_company_by_credentials(
        email=company_tenant.admin_email,
        password=req.password,
        extend_days=req.extend_days,
        new_plan_id=req.plan_id,
    )


# --- SUPERADMIN GOVERNANCE ENDPOINTS ---

def ensure_superadmin_only(request: Request):
    if getattr(request.state, "company_tenant", None):
        raise ForbiddenError("Only platform Superadmin can access company governance.")


@router.get("/companies", response_model=List[CompanyTenantOut])
async def list_companies(
    request: Request,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIGURE)),
    db: AsyncSession = Depends(get_master_db),
):
    """List all company tenants, their dedicated database names, and subscription status."""
    ensure_superadmin_only(request)
    service = CompanyService(db)
    return await service.list_companies()


@router.put("/plans/{plan_id}", response_model=SubscriptionPlanOut)
async def update_plan(
    plan_id: str,
    req: SubscriptionPlanUpdate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIGURE)),
    db: AsyncSession = Depends(get_master_db),
):
    """Superadmin update of plan pricing and feature flags."""
    ensure_superadmin_only(request)
    service = CompanyService(db)
    return await service.update_plan(plan_id, req)


@router.post("/companies/{company_id}/freeze", response_model=CompanyTenantOut)
async def freeze_company(
    company_id: str,
    req: CompanyFreezeRequest,
    request: Request,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIGURE)),
    db: AsyncSession = Depends(get_master_db),
):
    """Superadmin instant freeze: blocks access to the company's dedicated database."""
    ensure_superadmin_only(request)
    service = CompanyService(db)
    return await service.freeze_company(company_id, reason=req.reason or "Frozen by administrator")


@router.post("/companies/{company_id}/unfreeze", response_model=CompanyTenantOut)
async def unfreeze_company(
    company_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIGURE)),
    db: AsyncSession = Depends(get_master_db),
):
    """Superadmin instant unfreeze: restores company access."""
    ensure_superadmin_only(request)
    service = CompanyService(db)
    return await service.unfreeze_company(company_id)


@router.post("/companies/{company_id}/renew", response_model=CompanyTenantOut)
async def renew_company(
    company_id: str,
    req: CompanyRenewRequest,
    request: Request,
    current_user: User = Depends(require_permission(Permission.SYSTEM_CONFIGURE)),
    db: AsyncSession = Depends(get_master_db),
):
    """Superadmin renewal or extension of company subscription date."""
    ensure_superadmin_only(request)
    service = CompanyService(db)
    return await service.renew_company_subscription(company_id, req)
