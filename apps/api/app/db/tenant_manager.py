"""Tenant database manager supporting dedicated PostgreSQL databases per company."""
import os
import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.errors import ForbiddenError
from app.core.logging import logger
from app.core.rbac import ROLE_PERMISSIONS, Permission, RoleEnum
from app.core.security import hash_password
from app.db.base import Base
from app.models.entities import (
    CompanyTenant,
    Organization,
    OrganizationMember,
    PermissionModel,
    Role,
    User,
)

# In-memory pool of company async database engines
_tenant_engines: Dict[str, AsyncEngine] = {}


def sanitize_db_name(company_slug: str) -> str:
    """Generate a clean, safe SQL database identifier from company slug."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", company_slug.lower()).strip("_")
    return f"company_{clean}"[:63]


def get_company_engine(db_connection_url: str) -> AsyncEngine:
    """Get or create cached async engine for a company database."""
    if db_connection_url not in _tenant_engines:
        connect_args = {}
        if "sqlite" in db_connection_url:
            connect_args["check_same_thread"] = False
        _tenant_engines[db_connection_url] = create_async_engine(
            db_connection_url,
            connect_args=connect_args,
            future=True,
        )
    return _tenant_engines[db_connection_url]


async def create_company_database(company_slug: str) -> Tuple[str, str]:
    """
    Dynamically provision a dedicated database for a company.
    In PostgreSQL: executes CREATE DATABASE <db_name>.
    In SQLite: prepares dedicated file path in ./tenants directory.
    Returns (db_name, db_connection_url).
    """
    db_name = sanitize_db_name(company_slug)
    base_url = settings.DATABASE_URL

    if "postgresql" in base_url:
        parsed = urlparse(base_url)
        # Connect to existing database with autocommit to run CREATE DATABASE
        admin_engine = create_async_engine(base_url, isolation_level="AUTOCOMMIT", future=True)
        try:
            async with admin_engine.connect() as conn:
                check_query = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
                result = await conn.execute(check_query, {"dbname": db_name})
                if not result.scalar():
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    logger.info(f"Created dedicated PostgreSQL database: {db_name}")
                else:
                    logger.info(f"PostgreSQL database {db_name} already exists.")
        finally:
            await admin_engine.dispose()

        company_db_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            f"/{db_name}",
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
    else:
        # SQLite fallback for offline / test environments
        os.makedirs("./tenants", exist_ok=True)
        company_db_url = f"sqlite+aiosqlite:///./tenants/{db_name}.db"
        logger.info(f"Configured SQLite tenant database at {company_db_url}")

    # Initialize all tenant-scoped tables inside the new company database
    tenant_engine = get_company_engine(company_db_url)
    async with tenant_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"Successfully initialized all tables in {db_name}")

    return db_name, company_db_url


async def seed_company_database(
    company_db_url: str,
    company_name: str,
    company_slug: str,
    admin_full_name: str,
    admin_email: str,
    admin_password: str,
) -> User:
    """Seed standard roles, permissions, organization, and initial Admin in company DB."""
    tenant_engine = get_company_engine(company_db_url)
    session_factory = async_sessionmaker(bind=tenant_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        from sqlalchemy import select
        # 1. Seed Permissions & Roles in tenant database idempotently
        permissions_map = {}
        for perm in Permission:
            p_res = await session.execute(select(PermissionModel).where(PermissionModel.name == perm.value))
            p_obj = p_res.scalar_one_or_none()
            if not p_obj:
                p_obj = PermissionModel(name=perm.value, description=f"Permission for {perm.value}")
                session.add(p_obj)
                await session.flush()
            permissions_map[perm] = p_obj

        for role_enum in RoleEnum:
            r_res = await session.execute(select(Role).where(Role.name == role_enum.value))
            role_obj = r_res.scalar_one_or_none()
            if not role_obj:
                role_obj = Role(name=role_enum.value, description=f"{role_enum.value} role", is_system=True)
                assigned_perms = ROLE_PERMISSIONS.get(role_enum, set())
                role_obj.permissions = [permissions_map[p] for p in assigned_perms if p in permissions_map]
                session.add(role_obj)
                await session.flush()

        # 2. Seed Organization
        org_res = await session.execute(select(Organization).where(Organization.slug == company_slug))
        org = org_res.scalar_one_or_none()
        if not org:
            org = Organization(name=company_name, slug=company_slug)
            session.add(org)
            await session.flush()

        # 3. Seed Company Admin idempotently
        user_res = await session.execute(select(User).where(User.email == admin_email.lower()))
        user = user_res.scalar_one_or_none()
        if not user:
            user = User(
                email=admin_email.lower(),
                hashed_password=hash_password(admin_password),
                full_name=admin_full_name,
                is_active=True,
                is_verified=True,
                role=RoleEnum.ADMIN.value,
            )
            session.add(user)
            await session.flush()

            # 4. Link Member
            member = OrganizationMember(organization_id=org.id, user_id=user.id, role=RoleEnum.ADMIN.value)
            session.add(member)

        await session.commit()
        await session.refresh(user)
        return user


def verify_company_access(company: CompanyTenant) -> None:
    """Verify company workspace is not blocked and subscription has not expired."""
    if company.is_blocked:
        raise ForbiddenError(
            f"Workspace blocked by Superadmin: {company.blocked_reason or 'Contact support to restore access.'}"
        )

    now = datetime.now(timezone.utc)
    expires_at = company.subscription_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        raise ForbiddenError(
            f"Subscription expired on {expires_at.strftime('%Y-%m-%d')}. Please renew your plan to restore access."
        )
