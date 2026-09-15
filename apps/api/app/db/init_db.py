"""Database initialization and seeding of roles, superadmin, and default prompts."""
from datetime import datetime, timezone
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.core.rbac import ROLE_PERMISSIONS, RoleEnum, Permission
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.ai.gateway.gateway import llm_gateway
from app.models.entities import (
    User,
    Organization,
    OrganizationMember,
    Role,
    PermissionModel,
    LLMProviderModel,
    LLMModelConfig,
    PromptModel,
    PromptVersionModel,
)


DEFAULT_PROMPTS = {
    "research_planner": {
        "description": "Deconstructs blog topic into targeted search sub-queries and questions.",
        "agent_name": "ResearchPlanner",
        "system": "You are a senior content researcher and strategist. Break down topics into search queries, key questions, and required evidence.",
        "user_template": "Topic: {topic}\nTarget Audience: {target_audience}\nGuidelines: {guidelines}\n\nGenerate structured search plan.",
    },
    "source_validator": {
        "description": "Evaluates credibility of sources and tags factual claims.",
        "agent_name": "SourceValidator",
        "system": "You are a critical source verification specialist. Assess domain trustworthiness and verify supporting evidence.",
        "user_template": "Sources collected:\n{sources}\n\nValidate each source and extract core verifiable claims.",
    },
    "content_strategist": {
        "description": "Establishes angle, narrative hooks, and audience value proposition.",
        "agent_name": "ContentStrategist",
        "system": "You are a master digital content strategist. Develop unique editorial angles and reader retention strategies.",
        "user_template": "Topic: {topic}\nAudience: {target_audience}\nVerified Claims: {claims}\n\nFormulate the comprehensive content strategy.",
    },
    "outline_agent": {
        "description": "Generates hierarchical H1/H2/H3 outline with section goals and word count targets.",
        "agent_name": "OutlineAgent",
        "system": "You are an editorial architect. Create logical, comprehensive markdown outlines with explicit section guidelines.",
        "user_template": "Strategy: {strategy}\nTopic: {topic}\n\nProduce complete blog outline.",
    },
    "writer_agent": {
        "description": "Drafts long-form, engaging, authoritative articles with source citations.",
        "agent_name": "WriterAgent",
        "system": "You are an elite technology and industry writer. Produce authoritative, highly engaging, long-form content with markdown formatting and inline citations [Source N].",
        "user_template": "Outline:\n{outline}\n\nVerified Sources & Claims:\n{sources}\n\nBrand Voice: {brand_voice}\n\nWrite the complete article.",
    },
    "fact_checker": {
        "description": "Extracts claims from the draft and verifies them against ground truth sources.",
        "agent_name": "FactChecker",
        "system": "You are an uncompromising fact checker. Verify every assertion in the draft against the verified source corpus.",
        "user_template": "Article Draft:\n{content}\n\nGrounding Sources:\n{sources}\n\nAnalyze and verify all factual claims.",
    },
    "seo_agent": {
        "description": "Optimizes keyword density, generates meta tags, schema markup, and calculates SEO score.",
        "agent_name": "SEOAgent",
        "system": "You are a technical SEO expert. Optimize titles, meta descriptions, readability, heading structure, and JSON-LD schema.",
        "user_template": "Article Content:\n{content}\nTarget Keywords: {keywords}\n\nProvide exhaustive SEO analysis and score.",
    },
    "critic_agent": {
        "description": "Evaluates the article against quality rubrics and assigns a score from 0.0 to 10.0.",
        "agent_name": "CriticAgent",
        "system": "You are a senior executive editor. Critically evaluate tone, depth, readability, structure, and factual accuracy. Return score and structured issues.",
        "user_template": "Draft:\n{content}\nSEO Score: {seo_score}\nFact Check: {fact_check}\n\nEvaluate and score the draft.",
    },
    "editor_agent": {
        "description": "Refines and revises the draft based on critic feedback.",
        "agent_name": "EditorAgent",
        "system": "You are a meticulous revision editor. Polish the draft to directly address all issues identified by the critic.",
        "user_template": "Draft:\n{content}\nCritic Issues:\n{issues}\n\nRevise and elevate the draft.",
    },
}


async def init_db(session: AsyncSession) -> None:
    """Initialize database tables and seed baseline records."""
    legacy_roles = {
        "SUPER_ADMIN": RoleEnum.ADMIN.value,
        "EDITOR": RoleEnum.PORTAL_USER.value,
        "AUTHOR": RoleEnum.PORTAL_USER.value,
        "VIEWER": RoleEnum.PUBLIC_USER.value,
    }
    for legacy, replacement in legacy_roles.items():
        await session.execute(update(User).where(User.role == legacy).values(role=replacement))
        await session.execute(update(OrganizationMember).where(OrganizationMember.role == legacy).values(role=replacement))

    # 1. Create permissions and roles
    permissions_map = {}
    for perm in Permission:
        res = await session.execute(select(PermissionModel).where(PermissionModel.name == perm.value))
        p_obj = res.scalar_one_or_none()
        if not p_obj:
            p_obj = PermissionModel(name=perm.value, description=f"Permission for {perm.value}")
            session.add(p_obj)
            await session.flush()
        permissions_map[perm] = p_obj

    for role_enum in RoleEnum:
        res = await session.execute(select(Role).where(Role.name == role_enum.value))
        role_obj = res.scalar_one_or_none()
        if not role_obj:
            role_obj = Role(name=role_enum.value, description=f"{role_enum.value} role", is_system=True)
            assigned_perms = ROLE_PERMISSIONS.get(role_enum, set())
            role_obj.permissions = [permissions_map[p] for p in assigned_perms if p in permissions_map]
            session.add(role_obj)
            await session.flush()

    # 2. Seed Default Organization
    res = await session.execute(select(Organization).where(Organization.slug == "default-org"))
    org = res.scalar_one_or_none()
    if not org:
        org = Organization(name="Primary Organization", slug="default-org")
        session.add(org)
        await session.flush()

    # 3. Bootstrap administrator from server-only environment variables.
    # No default password is embedded in source code or sent to the public UI.
    if settings.INITIAL_ADMIN_EMAIL and settings.INITIAL_ADMIN_PASSWORD:
        admin_email = settings.INITIAL_ADMIN_EMAIL.lower()
        res = await session.execute(select(User).where(User.email == admin_email))
        admin = res.scalar_one_or_none()
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=hash_password(settings.INITIAL_ADMIN_PASSWORD),
                full_name="Platform Administrator",
                is_active=True,
                is_verified=True,
                role=RoleEnum.ADMIN.value,
            )
            session.add(admin)
            await session.flush()
            session.add(OrganizationMember(organization_id=org.id, user_id=admin.id, role=RoleEnum.ADMIN.value))
        elif settings.RESET_INITIAL_ADMIN_PASSWORD:
            admin.hashed_password = hash_password(settings.INITIAL_ADMIN_PASSWORD)
            admin.is_active = True
            logger.warning("Bootstrap administrator password was reset from server-side configuration.")
    else:
        logger.warning("No bootstrap administrator configured. Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD server-side.")

    # 4. Seed Provider records
    providers_seed = [
        ("OpenAI", "OpenAI", "", settings.OPENAI_API_KEY is not None),
        ("Gemini", "Google Gemini", "", settings.GEMINI_API_KEY is not None),
        ("Claude", "Anthropic Claude", "", settings.ANTHROPIC_API_KEY is not None),
        ("Grok", "xAI Grok", "", settings.XAI_API_KEY is not None),
    ]

    has_active = False
    for name, display_name, default_model, has_key in providers_seed:
        res = await session.execute(select(LLMProviderModel).where(LLMProviderModel.name == name))
        prov = res.scalar_one_or_none()
        status_val = "CONNECTED" if has_key else "NOT_CONFIGURED"
        
        if not prov:
            is_active = False
            if has_key and not has_active:
                is_active = True
                has_active = True

            prov = LLMProviderModel(
                name=name,
                display_name=display_name,
                is_active=is_active,
                is_enabled=True,
                default_model=default_model,
                connection_status=status_val,
            )
            session.add(prov)
            await session.flush()

            # Add default model
            m_config = LLMModelConfig(
                provider_id=prov.id,
                model_name=default_model,
                display_name=default_model,
                is_default=True
            )
            session.add(m_config)

    # 5. Seed Prompt Templates
    for prompt_key, p_info in DEFAULT_PROMPTS.items():
        res = await session.execute(select(PromptModel).where(PromptModel.name == prompt_key))
        p_obj = res.scalar_one_or_none()
        if not p_obj:
            p_obj = PromptModel(
                name=prompt_key,
                description=p_info["description"],
                agent_name=p_info["agent_name"],
                current_version=1
            )
            session.add(p_obj)
            await session.flush()

            v_obj = PromptVersionModel(
                prompt_id=p_obj.id,
                version_number=1,
                system_prompt=p_info["system"],
                user_template=p_info["user_template"],
                is_active=True
            )
            session.add(v_obj)

    await session.commit()
    logger.info("Database initialized and seeded successfully.")


async def create_tables_and_seed() -> None:
    """Create all tables and seed data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await init_db(session)
        # Reapply database-backed model selections after every API start or hot reload.
        # Provider credentials still come only from server-side environment/secrets.
        result = await session.execute(select(LLMProviderModel))
        providers = list(result.scalars().all())
        for provider in providers:
            if provider.name in llm_gateway.get_configured_providers() and provider.default_model.strip():
                llm_gateway.set_provider_model(provider.name, provider.default_model)

        active_provider = next((provider for provider in providers if provider.is_active), None)
        if (
            active_provider
            and active_provider.name in llm_gateway.get_configured_providers()
            and active_provider.default_model.strip()
        ):
            llm_gateway.set_active_provider(active_provider.name, active_provider.default_model)
        logger.info("Persisted provider model selections restored into the LLM gateway.")
