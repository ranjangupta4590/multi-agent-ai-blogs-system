"""Admin dashboard and governance endpoints."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.entities import User
from app.schemas.schemas import AnalyticsSummaryOut, AuditLogOut, UserOut, UserRoleUpdate
from app.services.admin_service import AdminService
from app.services.auth_service import require_permission

router = APIRouter()


class ToggleActiveRequest(BaseModel):
    is_active: bool


class CreatePromptVersionRequest(BaseModel):
    system_prompt: str
    user_template: str


@router.get("/users", response_model=List[UserOut])
async def list_users(
    current_user: User = Depends(require_permission(Permission.USERS_READ)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_users()


@router.put("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: str,
    req: UserRoleUpdate,
    current_user: User = Depends(require_permission(Permission.USERS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.update_user_role(user_id, req.role, current_user)


@router.put("/users/{user_id}/active", response_model=UserOut)
async def toggle_user_active(
    user_id: str,
    req: ToggleActiveRequest,
    current_user: User = Depends(require_permission(Permission.USERS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.toggle_user_active(user_id, req.is_active, current_user)


@router.get("/prompts")
async def list_prompts(
    current_user: User = Depends(require_permission(Permission.PROMPTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_prompts()


@router.post("/prompts/{prompt_id}/versions")
async def create_prompt_version(
    prompt_id: str,
    req: CreatePromptVersionRequest,
    current_user: User = Depends(require_permission(Permission.PROMPTS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    new_v = await service.create_prompt_version(
        prompt_id, req.system_prompt, req.user_template, current_user
    )
    return {
        "message": f"Prompt version {new_v.version_number} published successfully",
        "version": new_v.version_number,
    }


@router.get("/audit-logs", response_model=List[AuditLogOut])
async def list_audit_logs(
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(require_permission(Permission.AUDIT_LOGS_READ)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_audit_logs(limit=limit)


@router.get("/analytics", response_model=AnalyticsSummaryOut)
async def get_analytics_summary(
    current_user: User = Depends(require_permission(Permission.USERS_READ)),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_analytics_summary()
