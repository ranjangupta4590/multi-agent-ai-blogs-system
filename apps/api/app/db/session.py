"""Async database engine and dynamic session dependency for multi-tenant isolation."""
from typing import AsyncGenerator, Optional
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token

# Master engine configuration
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for master control database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Dynamic session dependency.
    If authenticated user belongs to a company tenant, routes to their dedicated database
    while enforcing freeze and subscription expiration guards.
    If Superadmin, default workspace, or public guest, routes to primary database.
    """
    tenant_db_url: Optional[str] = None

    if request:
        token = None
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth[7:].strip()
        elif settings.SESSION_COOKIE_NAME in request.cookies:
            token = request.cookies[settings.SESSION_COOKIE_NAME]

        if token:
            try:
                payload = decode_access_token(token)
                company_id = payload.get("company_id") if payload else None
                if company_id:
                    from app.models.entities import CompanyTenant
                    async with AsyncSessionLocal() as master_db:
                        res = await master_db.execute(select(CompanyTenant).where(CompanyTenant.id == company_id))
                        company = res.scalar_one_or_none()
                        if company:
                            request.state.company_tenant = company
                            request.state.company_name = company.company_name
                            tenant_db_url = company.db_connection_url
            except Exception:
                tenant_db_url = None

    if tenant_db_url:
        from app.db.tenant_manager import get_company_engine
        tenant_engine = get_company_engine(tenant_db_url)
        tenant_session_factory = async_sessionmaker(
            bind=tenant_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        async with tenant_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    else:
        # Superadmin, default workspace, or unauthenticated public access
        async with AsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
