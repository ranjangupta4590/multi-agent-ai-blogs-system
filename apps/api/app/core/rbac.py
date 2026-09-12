"""Role-Based Access Control (RBAC) definitions and permission checks."""
from enum import Enum
from typing import Dict, List, Set
from fastapi import Depends
from app.core.errors import ForbiddenError, UnauthorizedError


class RoleEnum(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    AUTHOR = "AUTHOR"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    USERS_READ = "users.read"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DELETE = "users.delete"

    ORGANIZATIONS_READ = "organizations.read"
    ORGANIZATIONS_UPDATE = "organizations.update"

    PROJECTS_READ = "projects.read"
    PROJECTS_CREATE = "projects.create"
    PROJECTS_UPDATE = "projects.update"
    PROJECTS_DELETE = "projects.delete"

    ARTICLES_READ = "articles.read"
    ARTICLES_CREATE = "articles.create"
    ARTICLES_UPDATE = "articles.update"
    ARTICLES_DELETE = "articles.delete"
    ARTICLES_PUBLISH = "articles.publish"

    RESEARCH_RUN = "research.run"
    AGENTS_READ = "agents.read"
    AGENTS_RUN = "agents.run"
    AGENTS_CONFIGURE = "agents.configure"

    PROVIDERS_READ = "providers.read"
    PROVIDERS_CONFIGURE = "providers.configure"

    PROMPTS_READ = "prompts.read"
    PROMPTS_CREATE = "prompts.create"
    PROMPTS_UPDATE = "prompts.update"

    AUDIT_LOGS_READ = "audit_logs.read"
    SYSTEM_CONFIGURE = "system.configure"


# Default Role-to-Permissions Mapping
ROLE_PERMISSIONS: Dict[RoleEnum, Set[Permission]] = {
    RoleEnum.SUPER_ADMIN: {p for p in Permission},
    RoleEnum.ADMIN: {
        Permission.USERS_READ, Permission.USERS_CREATE, Permission.USERS_UPDATE,
        Permission.ORGANIZATIONS_READ, Permission.ORGANIZATIONS_UPDATE,
        Permission.PROJECTS_READ, Permission.PROJECTS_CREATE, Permission.PROJECTS_UPDATE, Permission.PROJECTS_DELETE,
        Permission.ARTICLES_READ, Permission.ARTICLES_CREATE, Permission.ARTICLES_UPDATE, Permission.ARTICLES_DELETE, Permission.ARTICLES_PUBLISH,
        Permission.RESEARCH_RUN,
        Permission.AGENTS_READ, Permission.AGENTS_RUN, Permission.AGENTS_CONFIGURE,
        Permission.PROVIDERS_READ, Permission.PROVIDERS_CONFIGURE,
        Permission.PROMPTS_READ, Permission.PROMPTS_CREATE, Permission.PROMPTS_UPDATE,
        Permission.AUDIT_LOGS_READ,
    },
    RoleEnum.EDITOR: {
        Permission.PROJECTS_READ, Permission.PROJECTS_CREATE, Permission.PROJECTS_UPDATE,
        Permission.ARTICLES_READ, Permission.ARTICLES_CREATE, Permission.ARTICLES_UPDATE, Permission.ARTICLES_PUBLISH,
        Permission.RESEARCH_RUN,
        Permission.AGENTS_READ, Permission.AGENTS_RUN,
        Permission.PROVIDERS_READ,
        Permission.PROMPTS_READ,
    },
    RoleEnum.AUTHOR: {
        Permission.PROJECTS_READ,
        Permission.ARTICLES_READ, Permission.ARTICLES_CREATE, Permission.ARTICLES_UPDATE,
        Permission.RESEARCH_RUN,
        Permission.AGENTS_READ, Permission.AGENTS_RUN,
        Permission.PROVIDERS_READ,
    },
    RoleEnum.VIEWER: {
        Permission.PROJECTS_READ,
        Permission.ARTICLES_READ,
        Permission.AGENTS_READ,
        Permission.PROVIDERS_READ,
    },
}


def user_has_permission(role: str, permission: Permission) -> bool:
    """Check if a given role name has the specified permission."""
    try:
        role_enum = RoleEnum(role)
        return permission in ROLE_PERMISSIONS.get(role_enum, set())
    except (ValueError, KeyError):
        return False


def get_role_permissions(role: str) -> List[str]:
    """Retrieve all permission string tokens assigned to a role."""
    try:
        role_enum = RoleEnum(role)
        return [p.value for p in ROLE_PERMISSIONS.get(role_enum, set())]
    except ValueError:
        return []
