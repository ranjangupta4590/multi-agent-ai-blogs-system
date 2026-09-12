"""Article service managing generation lifecycle, versioning, sources, and claims."""
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.gateway.gateway import llm_gateway
from app.ai.workflows.workflow_engine import BlogGenerationWorkflow
from app.core.errors import ForbiddenError, NotFoundError, NoProviderConfiguredError
from app.models.entities import (
    Article,
    ArticleVersion,
    AuditLog,
    Claim,
    Project,
    SEOAnalysis,
    Source,
    User,
)
from app.schemas.schemas import ArticleCreateWizard, ArticleUpdate


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", cleaned).strip("-")[:100]


class ArticleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_article(self, article_id: str, user: User, org_id: str) -> Article:
        """Fetch article with tenant ownership verification."""
        res = await self.db.execute(
            select(Article)
            .join(Project, Article.project_id == Project.id)
            .where(
                and_(
                    Article.id == article_id,
                    Project.organization_id == org_id,
                )
            )
        )
        article = res.scalar_one_or_none()
        if not article:
            raise NotFoundError("Article", article_id)
        return article

    async def list_articles(self, project_id: str, user: User, org_id: str) -> List[Article]:
        res = await self.db.execute(
            select(Article)
            .join(Project, Article.project_id == Project.id)
            .where(
                and_(
                    Article.project_id == project_id,
                    Project.organization_id == org_id,
                )
            )
            .order_by(Article.created_at.desc())
        )
        return list(res.scalars().all())

    async def create_article_draft(
        self, req: ArticleCreateWizard, user: User, org_id: str
    ) -> Article:
        # Verify project belongs to org
        proj_res = await self.db.execute(
            select(Project).where(
                and_(Project.id == req.project_id, Project.organization_id == org_id)
            )
        )
        project = proj_res.scalar_one_or_none()
        if not project:
            raise NotFoundError("Project", req.project_id)

        title = f"{req.topic.title()}: Comprehensive Guide"
        slug = slugify(req.topic)

        article = Article(
            project_id=project.id,
            author_id=user.id,
            title=title,
            slug=slug,
            topic=req.topic,
            content=f"# {title}\n\n*Draft initialized. AI generation pending.*",
            summary=req.content_goal,
            status="DRAFT",
            target_keywords=req.target_keywords,
            current_version=1,
        )
        self.db.add(article)
        await self.db.flush()

        # Create initial snapshot Version 1
        v1 = ArticleVersion(
            article_id=article.id,
            version_number=1,
            title=article.title,
            content=article.content,
            change_summary="Initial draft created",
            created_by=user.id,
        )
        self.db.add(v1)

        audit = AuditLog(
            user_id=user.id,
            organization_id=org_id,
            action="ARTICLE_CREATE_DRAFT",
            resource_type="ARTICLE",
            resource_id=article.id,
            details={"topic": article.topic, "title": article.title},
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def generate_article_content(
        self, article_id: str, user: User, org_id: str
    ) -> Article:
        """Run the 11-agent workflow and update the article."""
        article = await self.get_article(article_id, user, org_id)
        
        # Check that an AI provider is configured
        if not llm_gateway.is_operational():
            raise NoProviderConfiguredError(
                "Configure at least one AI provider to start generating content."
            )

        # Retrieve project context
        proj_res = await self.db.execute(select(Project).where(Project.id == article.project_id))
        project = proj_res.scalar_one()

        article.status = "GENERATING"
        await self.db.commit()

        initial_state = {
            "topic": article.topic,
            "target_audience": project.target_audience or "General Readers",
            "brand_voice": project.brand_voice or "Authoritative and engaging",
            "content_goal": article.summary or "Educate and build domain authority",
            "target_keywords": article.target_keywords,
            "total_cost_usd": article.total_cost_usd,
            "current_version": article.current_version,
        }

        workflow = BlogGenerationWorkflow()
        final_state = await workflow.run(initial_state)

        # Update article fields
        article.title = final_state.get("title", article.title)
        article.content = final_state.get("content", article.content)
        article.word_count = final_state.get("word_count", len(article.content.split()))
        article.estimated_reading_time = final_state.get("estimated_reading_time", 5)
        article.generated_by_provider = final_state.get("generated_by_provider", llm_gateway.active_provider_name)
        article.generated_by_model = final_state.get("generated_by_model", "standard")
        article.content_strategy = final_state.get("content_strategy", {})
        article.outline = final_state.get("outline", {})
        article.critic_evaluation = final_state.get("critic_evaluation", {})
        article.total_cost_usd = final_state.get("total_cost_usd", 0.0)
        article.status = "IN_REVIEW"  # Always transitions to Human Review before publishing
        article.current_version += 1

        # Save new version snapshot
        version_snapshot = ArticleVersion(
            article_id=article.id,
            version_number=article.current_version,
            title=article.title,
            content=article.content,
            change_summary="AI 11-agent generation completed",
            created_by="AI_AGENT",
        )
        self.db.add(version_snapshot)

        # Save sources
        for s_data in final_state.get("sources", []):
            source_obj = Source(
                article_id=article.id,
                title=s_data.get("title", "External Source"),
                url=s_data.get("url", "https://example.com"),
                domain=s_data.get("domain", "example.com"),
                source_type=s_data.get("source_type", "NEWS"),
                credibility_score=float(s_data.get("credibility_score", 0.9)),
                snippet=s_data.get("snippet", ""),
                is_verified=True,
            )
            self.db.add(source_obj)

        # Save claims
        for c_data in final_state.get("claims", []):
            claim_obj = Claim(
                article_id=article.id,
                claim_text=c_data.get("claim_text", ""),
                status=c_data.get("status", "VERIFIED"),
                confidence=float(c_data.get("confidence", 0.9)),
                notes=c_data.get("notes", "Corroborated by sources"),
            )
            self.db.add(claim_obj)

        # Save SEO analysis
        seo_data = final_state.get("seo_analysis", {})
        if seo_data:
            existing_seo = await self.db.execute(
                select(SEOAnalysis).where(SEOAnalysis.article_id == article.id)
            )
            seo_obj = existing_seo.scalar_one_or_none()
            if not seo_obj:
                seo_obj = SEOAnalysis(
                    article_id=article.id,
                    score=int(seo_data.get("score", 85)),
                    meta_title=seo_data.get("meta_title", article.title)[:255],
                    meta_description=seo_data.get("meta_description", "")[:500],
                    slug=seo_data.get("slug", article.slug)[:255],
                    focus_keywords=seo_data.get("focus_keywords", article.target_keywords),
                    heading_hierarchy_check=bool(seo_data.get("heading_hierarchy_check", True)),
                    readability_score=float(seo_data.get("readability_score", 75.0)),
                    faq_items=seo_data.get("faq_items", []),
                    schema_markup=seo_data.get("schema_markup", {}),
                    recommendations=seo_data.get("recommendations", []),
                )
                self.db.add(seo_obj)

        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def update_article_content(
        self, article_id: str, req: ArticleUpdate, user: User, org_id: str
    ) -> Article:
        """Manual editorial revision that increments version and logs changes."""
        article = await self.get_article(article_id, user, org_id)

        if req.title:
            article.title = req.title
        if req.content:
            article.content = req.content
            article.word_count = len(req.content.split())
            article.estimated_reading_time = max(1, round(article.word_count / 200))
        if req.summary:
            article.summary = req.summary
        if req.status:
            article.status = req.status

        article.current_version += 1

        # Create Version Snapshot
        version_snapshot = ArticleVersion(
            article_id=article.id,
            version_number=article.current_version,
            title=article.title,
            content=article.content,
            change_summary=req.change_summary or "Manual user edit",
            created_by=user.id,
        )
        self.db.add(version_snapshot)

        await self.db.commit()
        await self.db.refresh(article)
        return article

    async def get_article_versions(
        self, article_id: str, user: User, org_id: str
    ) -> List[ArticleVersion]:
        await self.get_article(article_id, user, org_id)
        res = await self.db.execute(
            select(ArticleVersion)
            .where(ArticleVersion.article_id == article_id)
            .order_by(ArticleVersion.version_number.desc())
        )
        return list(res.scalars().all())

    async def restore_version(
        self, article_id: str, version_number: int, user: User, org_id: str
    ) -> Article:
        article = await self.get_article(article_id, user, org_id)
        res = await self.db.execute(
            select(ArticleVersion).where(
                and_(
                    ArticleVersion.article_id == article_id,
                    ArticleVersion.version_number == version_number,
                )
            )
        )
        v = res.scalar_one_or_none()
        if not v:
            raise NotFoundError("ArticleVersion", version_number)

        article.title = v.title
        article.content = v.content
        article.current_version += 1

        new_snapshot = ArticleVersion(
            article_id=article.id,
            version_number=article.current_version,
            title=article.title,
            content=article.content,
            change_summary=f"Restored from version {version_number}",
            created_by=user.id,
        )
        self.db.add(new_snapshot)
        await self.db.commit()
        await self.db.refresh(article)
        return article
