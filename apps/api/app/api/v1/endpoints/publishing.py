"""Publishing endpoints."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.entities import User
from app.schemas.schemas import PublishingJobOut, WordPressPublishRequest
from app.services.auth_service import require_permission
from app.services.publishing_service import PublishingService

router = APIRouter()


@router.post("/wordpress", response_model=PublishingJobOut, status_code=status.HTTP_201_CREATED)
async def publish_to_wordpress(
    req: WordPressPublishRequest,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_PUBLISH)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = PublishingService(db)
    return await service.publish_to_wordpress(req, current_user, org_id)
