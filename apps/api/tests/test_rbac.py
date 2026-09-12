"""Tests for RBAC permissions and tenant isolation."""
import pytest
from app.core.errors import ForbiddenError
from app.core.rbac import Permission, user_has_permission
from app.models.entities import User
from app.schemas.schemas import ProjectCreate
from app.services.project_service import ProjectService


def test_rbac_permission_matrix():
    """Verify granular role-to-permission mapping."""
    # SUPER_ADMIN has all permissions
    assert user_has_permission("SUPER_ADMIN", Permission.SYSTEM_CONFIGURE) is True
    assert user_has_permission("SUPER_ADMIN", Permission.PROVIDERS_CONFIGURE) is True
    assert user_has_permission("SUPER_ADMIN", Permission.ARTICLES_PUBLISH) is True

    # ADMIN can configure providers and manage users
    assert user_has_permission("ADMIN", Permission.PROVIDERS_CONFIGURE) is True
    assert user_has_permission("ADMIN", Permission.ARTICLES_PUBLISH) is True

    # EDITOR can edit and publish articles, but CANNOT configure providers or system
    assert user_has_permission("EDITOR", Permission.ARTICLES_PUBLISH) is True
    assert user_has_permission("EDITOR", Permission.PROVIDERS_CONFIGURE) is False
    assert user_has_permission("EDITOR", Permission.USERS_CREATE) is False

    # AUTHOR can create and edit articles, but CANNOT publish or configure providers
    assert user_has_permission("AUTHOR", Permission.ARTICLES_CREATE) is True
    assert user_has_permission("AUTHOR", Permission.ARTICLES_PUBLISH) is False
    assert user_has_permission("AUTHOR", Permission.PROVIDERS_CONFIGURE) is False

    # VIEWER can only read articles, cannot create or edit
    assert user_has_permission("VIEWER", Permission.ARTICLES_READ) is True
    assert user_has_permission("VIEWER", Permission.ARTICLES_CREATE) is False
    assert user_has_permission("VIEWER", Permission.ARTICLES_PUBLISH) is False


@pytest.mark.asyncio
async def test_tenant_isolation_boundary(test_db_session):
    """Verify that User from Org A cannot access or create projects in Org B."""
    service = ProjectService(test_db_session)
    user_a = User(id="user_a", email="a@example.com", full_name="User A", role="AUTHOR")

    # User A tries to create project in non-existent or unauthorized org "org_b"
    with pytest.raises(ForbiddenError):
        await service.create_project(
            ProjectCreate(name="Org B Secret Project"),
            user=user_a,
            org_id="unauthorized_org_b",
        )
