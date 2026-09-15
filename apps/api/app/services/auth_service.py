"""Authentication and authorization services with Argon2id and RBAC."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import Depends, Header, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.rbac import Permission, RoleEnum, user_has_permission
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.entities import AuditLog, Organization, OrganizationMember, SessionModel, User
from app.schemas.schemas import TokenResponse, UserLogin, UserRegister


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, req: UserRegister, ip_address: Optional[str] = None) -> TokenResponse:
        # Check existing user
        res = await self.db.execute(select(User).where(User.email == req.email.lower()))
        if res.scalar_one_or_none():
            raise ConflictError("A user with this email address already exists.")

        # Create organization
        org = Organization(
            name=req.organization_name or f"{req.full_name}'s Org",
            slug=req.email.split("@")[0].lower() + "-org",
        )
        self.db.add(org)
        await self.db.flush()

        # Create user
        user = User(
            email=req.email.lower(),
            hashed_password=hash_password(req.password),
            full_name=req.full_name,
            is_active=True,
            is_verified=True,
            role=RoleEnum.PUBLIC_USER.value,
        )
        self.db.add(user)
        await self.db.flush()

        # Add member to org
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=RoleEnum.PUBLIC_USER.value,
        )
        self.db.add(member)

        # Audit Log
        audit = AuditLog(
            user_id=user.id,
            organization_id=org.id,
            action="AUTH_REGISTER",
            resource_type="USER",
            resource_id=user.id,
            details={"email": user.email, "role": user.role},
            ip_address=ip_address,
        )
        self.db.add(audit)
        await self.db.commit()

        # Create token
        token = create_access_token(
            subject=user.id,
            claims={"email": user.email, "role": user.role, "org_id": org.id}
        )

        return TokenResponse(
            access_token=token,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=org.id,
        )

    async def admin_signup(self, req: UserRegister, ip_address: Optional[str] = None) -> TokenResponse:
        """One-time Admin bootstrap. Once an Admin exists, only Admin invitations can create accounts."""
        admin_count = (await self.db.execute(select(func.count(User.id)).where(User.role == RoleEnum.ADMIN.value))).scalar() or 0
        if admin_count:
            raise ForbiddenError("Admin signup is closed. Ask an existing Admin to create an internal account.")
        res = await self.db.execute(select(User).where(User.email == req.email.lower()))
        if res.scalar_one_or_none():
            raise ConflictError("A user with this email address already exists.")
        org_res = await self.db.execute(select(Organization).where(Organization.slug == "default-org"))
        org = org_res.scalar_one_or_none()
        if not org:
            org = Organization(name="Primary Organization", slug="default-org")
            self.db.add(org)
            await self.db.flush()
        user = User(email=req.email.lower(), hashed_password=hash_password(req.password), full_name=req.full_name, is_active=True, is_verified=True, role=RoleEnum.ADMIN.value)
        self.db.add(user)
        await self.db.flush()
        self.db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=RoleEnum.ADMIN.value))
        self.db.add(AuditLog(user_id=user.id, organization_id=org.id, action="ADMIN_BOOTSTRAP", resource_type="USER", resource_id=user.id, details={"role": user.role}, ip_address=ip_address))
        await self.db.commit()
        token = create_access_token(subject=user.id, claims={"email": user.email, "role": user.role, "org_id": org.id})
        return TokenResponse(access_token=token, user_id=user.id, email=user.email, full_name=user.full_name, role=user.role, organization_id=org.id)

    async def login(self, req: UserLogin, ip_address: Optional[str] = None) -> TokenResponse:
        res = await self.db.execute(select(User).where(User.email == req.email.lower()))
        user = res.scalar_one_or_none()

        if not user or not verify_password(req.password, user.hashed_password):
            # Log failed attempt
            audit = AuditLog(
                user_id=user.id if user else None,
                action="AUTH_LOGIN_FAILED",
                resource_type="USER",
                details={"attempted_email": req.email},
                ip_address=ip_address,
            )
            self.db.add(audit)
            await self.db.commit()
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise ForbiddenError("This user account has been deactivated.")

        # Find primary organization
        org_res = await self.db.execute(
            select(OrganizationMember.organization_id).where(OrganizationMember.user_id == user.id)
        )
        org_id = org_res.scalar_one_or_none()

        # Successful login audit
        audit = AuditLog(
            user_id=user.id,
            organization_id=org_id,
            action="AUTH_LOGIN_SUCCESS",
            resource_type="USER",
            resource_id=user.id,
            details={"email": user.email},
            ip_address=ip_address,
        )
        self.db.add(audit)
        await self.db.commit()

        token = create_access_token(
            subject=user.id,
            claims={"email": user.email, "role": user.role, "org_id": org_id}
        )

        return TokenResponse(
            access_token=token,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            organization_id=org_id,
        )


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency extracting and verifying the authenticated User."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif settings.SESSION_COOKIE_NAME in request.cookies:
        token = request.cookies[settings.SESSION_COOKIE_NAME]

    if not token:
        raise UnauthorizedError("Authentication token is missing.")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Invalid or expired authentication token.")

    user_id = payload["sub"]
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("Authenticated user no longer exists.")
    if not user.is_active:
        raise ForbiddenError("User account has been deactivated.")

    # Attach tenant info to request state
    request.state.current_user = user
    request.state.organization_id = payload.get("org_id")
    return user


def require_permission(perm: Permission):
    """Factory creating an authorization dependency for a required permission."""
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(current_user.role, perm):
            raise ForbiddenError(f"Role '{current_user.role}' lacks required permission '{perm.value}'.")
        return current_user
    return permission_checker
