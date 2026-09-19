"""Unit tests for Superadmin plan management, multi-database company provisioning, and freeze/unfreeze lifecycle."""
from datetime import datetime, timedelta, timezone
import pytest
from app.core.errors import ForbiddenError
from app.models.entities import CompanyTenant, SubscriptionPlan, User
from app.schemas.schemas import (
    CompanyFreezeRequest,
    CompanyRenewRequest,
    StudioSignupRequest,
    SubscriptionPlanUpdate,
)
from app.services.company_service import CompanyService


@pytest.mark.asyncio
async def test_superadmin_plan_pricing_and_feature_update(test_db_session):
    """Test that Superadmin can edit subscription plan prices and feature toggles."""
    service = CompanyService(test_db_session)
    plans = await service.list_plans()
    assert len(plans) >= 2
    
    # Update Starter plan price from $29 to $39
    starter = next(p for p in plans if p.id == "starter_studio")
    updated = await service.update_plan(
        "starter_studio",
        SubscriptionPlanUpdate(price_monthly_usd=39.0, max_articles_monthly=15),
    )
    assert updated.price_monthly_usd == 39.0
    assert updated.max_articles_monthly == 15


@pytest.mark.asyncio
async def test_studio_signup_and_dedicated_database_creation(test_db_session):
    """Test studio onboarding creates company record, dedicated DB, and active 30-day subscription."""
    service = CompanyService(test_db_session)
    req = StudioSignupRequest(
        company_name="Acme Publishing Inc",
        full_name="Alice Admin",
        email="alice@acmepublishing.com",
        password="SecurePassword2026!",
        plan_id="pro_studio",
    )
    token_resp = await service.studio_signup(req)
    assert token_resp.access_token is not None
    assert token_resp.email == "alice@acmepublishing.com"
    assert token_resp.role == "ADMIN"

    # Verify company is listed in Master DB
    companies = await service.list_companies()
    acme = next(c for c in companies if c.slug == "acme-publishing-inc")
    assert acme.company_name == "Acme Publishing Inc"
    assert "acme_publishing_inc" in acme.db_name
    assert acme.subscription_status == "ACTIVE"
    assert not acme.is_blocked


@pytest.mark.asyncio
async def test_superadmin_freeze_and_unfreeze_company(test_db_session):
    """Test Superadmin 1-click freeze blocks company and unfreeze restores it."""
    service = CompanyService(test_db_session)
    req = StudioSignupRequest(
        company_name="Beta Editorial Co",
        full_name="Bob Admin",
        email="bob@betaeditorial.com",
        password="SecurePassword2026!",
        plan_id="starter_studio",
    )
    await service.studio_signup(req)
    companies = await service.list_companies()
    beta = next(c for c in companies if c.slug == "beta-editorial-co")

    # Freeze company
    frozen = await service.freeze_company(beta.id, reason="Manual freeze for audit")
    assert frozen.is_blocked is True
    assert frozen.subscription_status == "BLOCKED"
    assert frozen.blocked_reason == "Manual freeze for audit"

    # Unfreeze company
    unfrozen = await service.unfreeze_company(beta.id)
    assert unfrozen.is_blocked is False
    assert unfrozen.blocked_reason is None
    assert unfrozen.subscription_status == "ACTIVE"


@pytest.mark.asyncio
async def test_subscription_renewal_extends_expiration(test_db_session):
    """Test renewal extends the company's subscription date."""
    service = CompanyService(test_db_session)
    req = StudioSignupRequest(
        company_name="Gamma News Corp",
        full_name="Gina Admin",
        email="gina@gammanews.com",
        password="SecurePassword2026!",
        plan_id="pro_studio",
    )
    await service.studio_signup(req)
    companies = await service.list_companies()
    gamma = next(c for c in companies if c.slug == "gamma-news-corp")

    original_exp = gamma.subscription_expires_at
    renewed = await service.renew_company_subscription(gamma.id, CompanyRenewRequest(extend_days=60))
    assert renewed.subscription_expires_at > original_exp
    assert renewed.subscription_status == "ACTIVE"


@pytest.mark.asyncio
async def test_self_renewal_by_credentials(test_db_session):
    """Test company admin can self-renew using credentials."""
    service = CompanyService(test_db_session)
    req = StudioSignupRequest(
        company_name="Delta Press Co",
        full_name="David Admin",
        email="david@deltapress.com",
        password="SecurePassword2026!",
        plan_id="starter_studio",
    )
    await service.studio_signup(req)
    
    renewed = await service.renew_company_by_credentials(
        email="david@deltapress.com",
        password="SecurePassword2026!",
        extend_days=45,
    )
    assert renewed.company_name == "Delta Press Co"
    assert renewed.subscription_status == "ACTIVE"


@pytest.mark.asyncio
async def test_frozen_company_can_signin_but_blocked_from_workspace(test_db_session):
    """When company is frozen, admin can still login, but require_permission blocks workspace access."""
    from app.schemas.schemas import UserLogin
    from app.services.auth_service import AuthService, require_permission
    from app.core.rbac import Permission
    from starlette.requests import Request

    service = CompanyService(test_db_session)
    req = StudioSignupRequest(
        company_name="Epsilon Wire Inc",
        full_name="Evan Admin",
        email="evan@epsilonwire.com",
        password="SecurePassword2026!",
        plan_id="pro_studio",
    )
    await service.studio_signup(req)
    companies = await service.list_companies()
    epsilon = next(c for c in companies if c.slug == "epsilon-wire-inc")

    # Freeze company
    await service.freeze_company(epsilon.id, reason="Subscription expired")

    # 1. Admin CAN still log in
    auth_service = AuthService(test_db_session)
    token_resp = await auth_service.login(UserLogin(email="evan@epsilonwire.com", password="SecurePassword2026!"))
    assert token_resp.access_token is not None

    # Verify master DB AuditLog recorded success with user_id=None (preventing FK violation)
    from app.models.entities import AuditLog
    from sqlalchemy import select
    audit_res = await test_db_session.execute(
        select(AuditLog).where(AuditLog.action == "AUTH_LOGIN_SUCCESS")
    )
    audits = audit_res.scalars().all()
    assert any(a.user_id is None and a.details.get("company") == "epsilon-wire-inc" for a in audits)

    # 2. But require_permission blocks access to workspace resources
    mock_request = Request({
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token_resp.access_token}".encode())],
    })
    mock_request.state.company_tenant = epsilon

    checker = require_permission(Permission.ARTICLES_READ)
    with pytest.raises(ForbiddenError) as exc:
        await checker(mock_request, User(id="dummy", email="evan@epsilonwire.com", role="ADMIN"))
    assert "Workspace blocked" in str(exc.value)
