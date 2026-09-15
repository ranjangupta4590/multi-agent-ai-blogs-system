"""Project management service enforcing tenant isolation and IDOR defense."""
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenError, NotFoundError
from app.models.entities import AuditLog, OrganizationMember, Project, User
from app.schemas.schemas import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _verify_org_membership(self, user: User, org_id: str) -> None:
        """Enforce multi-tenant access boundary."""
        if user.role == "ADMIN":
            return
        res = await self.db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user.id,
                )
            )
        )
        if not res.scalar_one_or_none():
            raise ForbiddenError("You do not have access to this organization's projects.")

    async def list_projects(self, user: User, org_id: str) -> List[Project]:
        await self._verify_org_membership(user, org_id)
        res = await self.db.execute(
            select(Project).where(
                and_(
                    Project.organization_id == org_id,
                    Project.is_archived == False,
                )
            ).order_by(Project.created_at.desc())
        )
        return list(res.scalars().all())

    async def get_project(self, project_id: str, user: User, org_id: str) -> Project:
        await self._verify_org_membership(user, org_id)
        res = await self.db.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.organization_id == org_id,
                )
            )
        )
        project = res.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project", project_id)
        return project

    async def create_project(self, req: ProjectCreate, user: User, org_id: str) -> Project:
        await self._verify_org_membership(user, org_id)
        project = Project(
            organization_id=org_id,
            owner_id=user.id,
            name=req.name,
            description=req.description,
            brand_voice=req.brand_voice,
            target_audience=req.target_audience,
            industry=req.industry,
            language=req.language,
            country=req.country,
            tone=req.tone,
            content_guidelines=req.content_guidelines,
            seo_settings=req.seo_settings,
            publishing_settings=req.publishing_settings,
        )
        self.db.add(project)
        await self.db.flush()

        audit = AuditLog(
            user_id=user.id,
            organization_id=org_id,
            action="PROJECT_CREATE",
            resource_type="PROJECT",
            resource_id=project.id,
            details={"name": project.name},
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def update_project(
        self, project_id: str, req: ProjectUpdate, user: User, org_id: str
    ) -> Project:
        project = await self.get_project(project_id, user, org_id)
        update_data = req.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def archive_project(self, project_id: str, user: User, org_id: str) -> None:
        project = await self.get_project(project_id, user, org_id)
        project.is_archived = True
        await self.db.commit()
