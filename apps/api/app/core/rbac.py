"""The three supported BlogPilot roles and their server-enforced permissions."""
from enum import Enum
from typing import Dict, List, Set


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    PORTAL_USER = "PORTAL_USER"
    PUBLIC_USER = "PUBLIC_USER"


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


ROLE_PERMISSIONS: Dict[RoleEnum, Set[Permission]] = {
    # Internal platform operator: unrestricted access.
    RoleEnum.ADMIN: {permission for permission in Permission},
    # Invited workspace collaborator: authoring and agent work only.
    RoleEnum.PORTAL_USER: {
        Permission.PROJECTS_READ, Permission.PROJECTS_CREATE, Permission.PROJECTS_UPDATE,
        Permission.ARTICLES_READ, Permission.ARTICLES_CREATE, Permission.ARTICLES_UPDATE,
        Permission.RESEARCH_RUN, Permission.AGENTS_READ, Permission.AGENTS_RUN,
        Permission.PROVIDERS_READ,
    },
    # Public accounts never receive dashboard or internal API permissions.
    RoleEnum.PUBLIC_USER: set(),
}


ROLE_LABELS = {
    RoleEnum.ADMIN.value: "Admin",
    RoleEnum.PORTAL_USER.value: "Portal user",
    RoleEnum.PUBLIC_USER.value: "Public user",
}


def user_has_permission(role: str, permission: Permission) -> bool:
    try:
        return permission in ROLE_PERMISSIONS.get(RoleEnum(role), set())
    except ValueError:
        return False


def get_role_permissions(role: str) -> List[str]:
    try:
        return sorted(permission.value for permission in ROLE_PERMISSIONS.get(RoleEnum(role), set()))
    except ValueError:
        return []
