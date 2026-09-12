"""Tests for Article lifecycle, versioning snapshots, and version restoration."""
import pytest
from app.ai.gateway.gateway import llm_gateway
from app.ai.providers.mock_provider import MockProvider
from app.models.entities import Organization, OrganizationMember, Project, User
from app.schemas.schemas import ArticleCreateWizard, ArticleUpdate
from app.services.article_service import ArticleService


@pytest.mark.asyncio
async def test_article_versioning_and_restore(test_db_session):
    # Register mock provider
    llm_gateway.register_provider(MockProvider("OpenAI"), make_active=True)

    # Setup test org, user, and project
    org = Organization(name="Test Org", slug="test-org")
    test_db_session.add(org)
    await test_db_session.flush()

    user = User(
        email="writer@example.com",
        hashed_password="hash",
        full_name="Writer Person",
        role="AUTHOR",
    )
    test_db_session.add(user)
    await test_db_session.flush()

    member = OrganizationMember(organization_id=org.id, user_id=user.id, role="AUTHOR")
    test_db_session.add(member)

    project = Project(
        organization_id=org.id,
        owner_id=user.id,
        name="AI Innovations Blog",
    )
    test_db_session.add(project)
    await test_db_session.commit()

    service = ArticleService(test_db_session)

    # 1. Create Draft (Version 1 created)
    draft = await service.create_article_draft(
        ArticleCreateWizard(
            project_id=project.id,
            topic="Autonomous AI Microservices",
        ),
        user=user,
        org_id=org.id,
    )
    assert draft.current_version == 1

    versions_v1 = await service.get_article_versions(draft.id, user, org.id)
    assert len(versions_v1) == 1
    assert versions_v1[0].version_number == 1

    # 2. Update Draft manually (Version 2 created)
    updated = await service.update_article_content(
        draft.id,
        ArticleUpdate(title="Revised Title for Microservices", content="# Revised Content"),
        user=user,
        org_id=org.id,
    )
    assert updated.current_version == 2

    versions_v2 = await service.get_article_versions(draft.id, user, org.id)
    assert len(versions_v2) == 2

    # 3. Restore Version 1 (creates Version 3 with Version 1 content)
    restored = await service.restore_version(draft.id, version_number=1, user=user, org_id=org.id)
    assert restored.current_version == 3
    assert "Draft initialized" in restored.content
