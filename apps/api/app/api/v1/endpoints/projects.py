"""Project management endpoints."""
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.entities import User
from app.schemas.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.auth_service import get_current_user, require_permission
from app.services.project_service import ProjectService

router = APIRouter()


@router.get("/", response_model=List[ProjectOut])
async def list_projects(
    request: Request,
    current_user: User = Depends(require_permission(Permission.PROJECTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ProjectService(db)
    return await service.list_projects(current_user, org_id)


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.PROJECTS_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ProjectService(db)
    return await service.create_project(req, current_user, org_id)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.PROJECTS_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ProjectService(db)
    return await service.get_project(project_id, current_user, org_id)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.PROJECTS_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ProjectService(db)
    return await service.update_project(project_id, req, current_user, org_id)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.PROJECTS_DELETE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ProjectService(db)
    await service.archive_project(project_id, current_user, org_id)
