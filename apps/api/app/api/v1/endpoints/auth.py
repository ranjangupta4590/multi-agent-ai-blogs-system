"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit
from app.db.session import get_db
from app.models.entities import User
from app.schemas.schemas import TokenResponse, UserLogin, UserOut, UserRegister
from app.services.auth_service import AuthService, get_current_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegister,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"reg_{client_ip}", max_requests=10, window_seconds=60)

    auth_service = AuthService(db)
    token_resp = await auth_service.register(req, ip_address=client_ip)

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


@router.post("/admin-signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def admin_signup(
    req: UserRegister,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Bootstrap exactly one Admin when no Admin has been provisioned yet."""
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"admin_signup_{client_ip}", max_requests=3, window_seconds=3600)
    token_resp = await AuthService(db).admin_signup(req, ip_address=client_ip)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token_resp.access_token,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite=settings.SAME_SITE_POLICY,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return token_resp


@router.post("/login", response_model=TokenResponse)
async def login(
    req: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"login_{client_ip}", max_requests=settings.RATE_LIMIT_LOGIN_PER_MIN, window_seconds=60)

    auth_service = AuthService(db)
    token_resp = await auth_service.login(req, ip_address=client_ip)

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


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserOut)
async def get_me(request: Request, current_user: User = Depends(get_current_user)):
    company = getattr(request.state, "company_tenant", None)
    is_superadmin = (company is None and current_user.role == "ADMIN")
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        is_frozen=getattr(current_user, "is_frozen", False),
        subscription_status=getattr(current_user, "subscription_status", "ACTIVE"),
        subscription_expires_at=getattr(current_user, "subscription_expires_at", None),
        blocked_reason=getattr(current_user, "blocked_reason", None),
        company_name=company.company_name if company else None,
        is_superadmin=is_superadmin,
        plan_id=company.plan_id if company else None,
        db_name=company.db_name if company else None,
    )
