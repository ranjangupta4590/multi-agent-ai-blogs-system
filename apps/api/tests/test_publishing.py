"""Tests for PublishingProvider, approval safeguards, and WordPress syndication."""
import pytest
from app.core.errors import ForbiddenError, SSRFViolationError
from app.models.entities import Article, Organization, OrganizationMember, Project, User
from app.publishing.wordpress import WordPressProvider
from app.schemas.schemas import WordPressPublishRequest
from app.services.publishing_service import PublishingService


@pytest.mark.asyncio
async def test_publishing_safeguard_requires_editor_or_admin(test_db_session):
    """Viewer or Author role cannot publish articles without human editorial approval."""
    org = Organization(name="Publishing Org", slug="pub-org")
    test_db_session.add(org)
    await test_db_session.flush()

    author_user = User(
        email="author@example.com",
        hashed_password="hash",
        full_name="Junior Author",
        role="PORTAL_USER",  # Does not have publish permissions
    )
    test_db_session.add(author_user)
    await test_db_session.flush()

    project = Project(organization_id=org.id, name="Security Tech")
    test_db_session.add(project)
    await test_db_session.flush()

    article = Article(
        project_id=project.id,
        author_id=author_user.id,
        title="Unreviewed Article",
        slug="unreviewed-article",
        topic="Security",
        content="Draft content",
        status="IN_REVIEW",
    )
    test_db_session.add(article)
    await test_db_session.commit()

    service = PublishingService(test_db_session)
    pub_req = WordPressPublishRequest(
        article_id=article.id,
        site_url="https://external-blog.example.com",
        username="wp_admin",
        application_password="app_pass_secret",
        target_status="draft",
    )

    # AUTHOR attempting to publish directly is blocked by Human Review requirement
    with pytest.raises(ForbiddenError):
        await service.publish_to_wordpress(pub_req, author_user, org.id)


@pytest.mark.asyncio
async def test_publishing_blocks_ssrf_destinations():
    """Publishing to localhost or metadata IP is blocked by SSRF defense."""
    provider = WordPressProvider(
        site_url="http://127.0.0.1:8080",
        username="user",
        application_password="password",
    )
    with pytest.raises(SSRFViolationError):
        await provider.publish_article(
            title="Test",
            content="Content",
            slug="test",
        )


@pytest.mark.asyncio
async def test_superadmin_can_publish_article_publicly(test_db_session):
    """Super Admin has full authority to draft, approve, and publish articles publicly."""
    from app.services.article_service import ArticleService
    from app.schemas.schemas import ArticleCreateWizard, ArticleUpdate

    org = Organization(name="Master Org", slug="master-org")
    test_db_session.add(org)
    await test_db_session.flush()

    admin_user = User(
        email="superadmin@blogpilot.internal",
        hashed_password="hash",
        full_name="Super Admin",
        role="ADMIN",
    )
    test_db_session.add(admin_user)
    await test_db_session.flush()

    project = Project(organization_id=org.id, name="Platform Blogs")
    test_db_session.add(project)
    await test_db_session.flush()

    service = ArticleService(test_db_session)
    draft = await service.create_article_draft(
        ArticleCreateWizard(
            project_id=project.id,
            topic="Next-Gen Autonomous AI Agents",
            target_keywords=["autonomous ai", "multi-agent systems"],
            brand_voice="Authoritative",
            guidelines="Deep technical breakdown",
        ),
        user=admin_user,
        org_id=org.id,
    )
    assert draft.status == "DRAFT"

    # Superadmin updates content and publishes
    published = await service.update_article_content(
        article_id=draft.id,
        req=ArticleUpdate(
            title="Next-Gen Autonomous AI Agents: The 2026 Guide",
            content="# Next-Gen Autonomous AI Agents\n\nDeep dive into agent architecture...",
            status="PUBLISHED",
            change_summary="Superadmin approved and published",
        ),
        user=admin_user,
        org_id=org.id,
    )
    assert published.status == "PUBLISHED"
    assert published.title == "Next-Gen Autonomous AI Agents: The 2026 Guide"
