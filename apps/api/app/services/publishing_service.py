"""Publishing service handling syndication, approval safeguards, and audit records."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.models.entities import Article, AuditLog, PublishingJob, User
from app.publishing.wordpress import WordPressProvider
from app.schemas.schemas import WordPressPublishRequest


class PublishingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def publish_to_wordpress(
        self, req: WordPressPublishRequest, user: User, org_id: str
    ) -> PublishingJob:
        res = await self.db.execute(select(Article).where(Article.id == req.article_id))
        article = res.scalar_one_or_none()
        if not article:
            raise NotFoundError("Article", req.article_id)

        # Human Review Safeguard: Check that user has authority to publish
        if user.role not in ("SUPER_ADMIN", "ADMIN", "EDITOR"):
            raise ForbiddenError("You must be an Editor or Admin to publish articles.")

        # Create job entry
        job = PublishingJob(
            article_id=article.id,
            platform="WORDPRESS",
            target_status=req.target_status,
            status="IN_PROGRESS",
        )
        self.db.add(job)
        await self.db.flush()

        # Instantiate provider
        provider = WordPressProvider(
            site_url=req.site_url,
            username=req.username,
            application_password=req.application_password,
        )

        result = await provider.publish_article(
            title=article.title,
            content=article.content,
            slug=article.slug,
            target_status=req.target_status,
            meta_description=article.summary,
            keywords=article.target_keywords,
        )

        job.completed_at = datetime.now(timezone.utc)
        if result.is_success:
            job.status = "COMPLETED"
            job.published_url = result.published_url
            if req.target_status == "publish":
                article.status = "PUBLISHED"
            audit_action = "ARTICLE_PUBLISHED"
        else:
            job.status = "FAILED"
            job.error_message = result.error_message
            audit_action = "ARTICLE_PUBLISH_FAILED"

        audit = AuditLog(
            user_id=user.id,
            organization_id=org_id,
            action=audit_action,
            resource_type="ARTICLE",
            resource_id=article.id,
            details={
                "platform": "WORDPRESS",
                "site_url": req.site_url,
                "status": job.status,
                "error": job.error_message,
            },
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(job)
        return job
