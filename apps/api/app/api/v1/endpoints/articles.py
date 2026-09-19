"""Article management and AI generation endpoints with SSE event streaming."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rbac import Permission
from app.db.session import get_db
from app.models.entities import Article, Claim, SEOAnalysis, Source, User
from app.schemas.schemas import (
    ArticleCreateWizard,
    ArticleOut,
    ArticleUpdate,
    ArticleVersionOut,
    ClaimOut,
    SEOAnalysisOut,
    SourceOut,
)
from app.services.article_service import ArticleService
from app.services.auth_service import get_current_user, require_permission

router = APIRouter()


@router.get("/", response_model=List[ArticleOut])
async def list_articles(
    project_id: str = Query(...),
    request: Request = None,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.list_articles(project_id, current_user, org_id)


@router.post("/", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
async def create_article_draft(
    req: ArticleCreateWizard,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.create_article_draft(req, current_user, org_id)


@router.post("/{article_id}/cancel", response_model=ArticleOut)
async def cancel_article_generation(article_id: str, request: Request, current_user: User = Depends(require_permission(Permission.ARTICLES_UPDATE)), db: AsyncSession = Depends(get_db)):
    service = ArticleService(db)
    article = await service.get_article(article_id, current_user, request.state.organization_id)
    article.status = "DRAFT"
    await db.commit()
    await db.refresh(article)
    return article

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(article_id: str, request: Request, current_user: User = Depends(require_permission(Permission.ARTICLES_DELETE)), db: AsyncSession = Depends(get_db)):
    service = ArticleService(db)
    article = await service.get_article(article_id, current_user, request.state.organization_id)
    await db.delete(article)
    await db.commit()

@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.get_article(article_id, current_user, org_id)


@router.put("/{article_id}", response_model=ArticleOut)
async def update_article(
    article_id: str,
    req: ArticleUpdate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.update_article_content(article_id, req, current_user, org_id)


@router.post("/{article_id}/generate", response_model=ArticleOut)
async def generate_article_content(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.AGENTS_RUN)),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the 11-agent autonomous generation pipeline."""
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.generate_article_content(article_id, current_user, org_id)


@router.get("/{article_id}/workflow/progress")
async def get_workflow_progress(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve real-time agent workflow execution progress for an article."""
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.get_workflow_progress(article_id, current_user, org_id)


@router.get("/{article_id}/versions", response_model=List[ArticleVersionOut])
async def get_article_versions(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.get_article_versions(article_id, current_user, org_id)


@router.post("/{article_id}/versions/{version_number}/restore", response_model=ArticleOut)
async def restore_article_version(
    article_id: str,
    version_number: int,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    return await service.restore_version(article_id, version_number, current_user, org_id)


@router.get("/{article_id}/sources", response_model=List[SourceOut])
async def get_article_sources(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    await service.get_article(article_id, current_user, org_id)

    res = await db.execute(
        select(Source).where(Source.article_id == article_id).order_by(Source.created_at.asc())
    )
    return list(res.scalars().all())


@router.get("/{article_id}/claims", response_model=List[ClaimOut])
async def get_article_claims(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    await service.get_article(article_id, current_user, org_id)

    res = await db.execute(
        select(Claim).where(Claim.article_id == article_id).order_by(Claim.created_at.asc())
    )
    return list(res.scalars().all())


@router.get("/{article_id}/seo", response_model=Optional[SEOAnalysisOut])
async def get_article_seo(
    article_id: str,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ARTICLES_READ)),
    db: AsyncSession = Depends(get_db),
):
    org_id = request.state.organization_id
    service = ArticleService(db)
    await service.get_article(article_id, current_user, org_id)

    res = await db.execute(select(SEOAnalysis).where(SEOAnalysis.article_id == article_id))
    return res.scalar_one_or_none()


