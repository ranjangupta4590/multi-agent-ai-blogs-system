"""AI Provider management endpoints with zero secret leakage."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.gateway.gateway import llm_gateway
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.entities import User
from app.schemas.schemas import (
    ProviderConfigureRequest,
    ProviderStatusOut,
    SetActiveProviderRequest,
)
from app.services.admin_service import AdminService
from app.services.auth_service import require_permission

router = APIRouter()


@router.get("/", response_model=List[ProviderStatusOut])
async def list_providers(
    current_user: User = Depends(require_permission(Permission.PROVIDERS_READ)),
):
    """Retrieve safe metadata on AI providers (never includes API keys)."""
    return llm_gateway.get_provider_metadata()


@router.post("/active")
async def set_active_provider(
    req: SetActiveProviderRequest,
    current_user: User = Depends(require_permission(Permission.PROVIDERS_CONFIGURE)),
    db: AsyncSession = Depends(get_db),
):
    """Switch the system-wide active AI provider."""
    admin_service = AdminService(db)
    await admin_service.set_active_provider(req.provider_name, req.model_name, current_user)
    return {
        "message": f"Active AI provider successfully set to '{req.provider_name}'",
        "active_provider": req.provider_name,
        "active_model": req.model_name,
    }


@router.post("/configure", status_code=status.HTTP_200_OK)
async def configure_provider(
    req: ProviderConfigureRequest,
    current_user: User = Depends(require_permission(Permission.PROVIDERS_CONFIGURE)),
    db: AsyncSession = Depends(get_db),
):
    """Securely configure credentials for a provider on the server side."""
    admin_service = AdminService(db)
    await admin_service.configure_provider_key(
        req.provider_name, req.api_key, req.default_model, current_user
    )
    return {
        "message": f"Provider '{req.provider_name}' configured successfully",
        "status": "CONNECTED",
    }


@router.get("/{provider_name}/health")
async def check_provider_health(
    provider_name: str,
    current_user: User = Depends(require_permission(Permission.PROVIDERS_READ)),
):
    """Execute live connectivity health check without exposing credentials."""
    status_res = await llm_gateway.check_provider_health(provider_name)
    return {
        "provider": provider_name,
        "is_healthy": status_res.is_healthy,
        "latency_ms": status_res.latency_ms,
        "message": status_res.message,
    }
