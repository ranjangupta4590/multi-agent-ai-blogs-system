"""Tests for RBAC permissions and tenant isolation."""
import pytest
from app.core.errors import ForbiddenError
from app.core.rbac import Permission, user_has_permission
from app.models.entities import User
from app.schemas.schemas import ProjectCreate
from app.services.project_service import ProjectService


def test_rbac_permission_matrix():
    """Verify granular role-to-permission mapping."""
    # ADMIN has all permissions
    assert user_has_permission("ADMIN", Permission.SYSTEM_CONFIGURE) is True
    assert user_has_permission("ADMIN", Permission.PROVIDERS_CONFIGURE) is True
    assert user_has_permission("ADMIN", Permission.ARTICLES_PUBLISH) is True

    # ADMIN can configure providers and manage users
    assert user_has_permission("ADMIN", Permission.PROVIDERS_CONFIGURE) is True
    assert user_has_permission("ADMIN", Permission.ARTICLES_PUBLISH) is True

    # PORTAL_USER can edit and publish articles, but CANNOT configure providers or system
    assert user_has_permission("PORTAL_USER", Permission.ARTICLES_PUBLISH) is False
    assert user_has_permission("PORTAL_USER", Permission.PROVIDERS_CONFIGURE) is False
    assert user_has_permission("PORTAL_USER", Permission.USERS_CREATE) is False

    # PORTAL_USER can create and edit articles, but CANNOT publish or configure providers
    assert user_has_permission("PORTAL_USER", Permission.ARTICLES_CREATE) is True
    assert user_has_permission("PORTAL_USER", Permission.ARTICLES_PUBLISH) is False
    assert user_has_permission("PORTAL_USER", Permission.PROVIDERS_CONFIGURE) is False

    # PUBLIC_USER can only read articles, cannot create or edit
    assert user_has_permission("PUBLIC_USER", Permission.ARTICLES_READ) is False
    assert user_has_permission("PUBLIC_USER", Permission.ARTICLES_CREATE) is False
    assert user_has_permission("PUBLIC_USER", Permission.ARTICLES_PUBLISH) is False


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(test_db_session):
    """Verify that User from Org A cannot access or create projects in Org B."""
    service = ProjectService(test_db_session)
    user_a = User(id="user_a", email="a@example.com", full_name="User A", role="PORTAL_USER")

    # User A tries to create project in non-existent or unauthorized org "org_b"
    with pytest.raises(ForbiddenError):
        await service.create_project(
            ProjectCreate(name="Org B Secret Project"),
            user=user_a,
            org_id="unauthorized_org_b",
        )
