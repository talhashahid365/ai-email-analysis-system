"""Central authorization — every endpoint must use can() or require() for permission checks.

Never scatter ad-hoc role checks in route handlers.
All authorization logic lives here so the permissions matrix stays in sync with /docs/permissions.md
"""
from enum import Enum
from fastapi import HTTPException, status
from app.models import User


class Action(str, Enum):
    # Email actions
    EMAIL_READ = "email:read"
    EMAIL_CREATE = "email:create"
    EMAIL_DELETE = "email:delete"
    # AI actions
    AI_ANALYZE = "ai:analyze"
    AI_REPLY = "ai:reply"
    AI_CHAT = "ai:chat"
    # Analytics
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_ADVANCED = "analytics:advanced"
    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_AUDIT = "admin:audit"
    ADMIN_CATEGORIES = "admin:categories"
    # Manager
    MANAGER_TEAM = "manager:team"
    # Notifications
    NOTIFICATIONS_READ = "notifications:read"
    # Tasks
    TASKS_READ = "tasks:read"
    TASKS_WRITE = "tasks:write"


# Role -> allowed actions mapping (mirrors /docs/permissions.md)
_ROLE_PERMISSIONS: dict[str, set[Action]] = {
    "user": {
        Action.EMAIL_READ,
        Action.EMAIL_CREATE,
        Action.EMAIL_DELETE,
        Action.AI_ANALYZE,
        Action.AI_REPLY,
        Action.AI_CHAT,
        Action.ANALYTICS_READ,
        Action.NOTIFICATIONS_READ,
        Action.TASKS_READ,
        Action.TASKS_WRITE,
    },
    "manager": {
        Action.EMAIL_READ,
        Action.EMAIL_CREATE,
        Action.EMAIL_DELETE,
        Action.AI_ANALYZE,
        Action.AI_REPLY,
        Action.AI_CHAT,
        Action.ANALYTICS_READ,
        Action.ANALYTICS_ADVANCED,
        Action.MANAGER_TEAM,
        Action.NOTIFICATIONS_READ,
        Action.TASKS_READ,
        Action.TASKS_WRITE,
    },
    "admin": set(Action),  # admins can do everything
}


def can(user: User, action: Action) -> bool:
    """Return True if the user has permission to perform action."""
    role = getattr(user, "role", "user") or "user"
    return action in _ROLE_PERMISSIONS.get(role, set())


def require(user: User, action: Action) -> None:
    """Raise HTTP 403 if user cannot perform action."""
    if not can(user, action):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {action}",
        )


def require_admin(user: User) -> None:
    """Raise HTTP 403 if user is not admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def require_admin_or_manager(user: User) -> None:
    """Raise HTTP 403 if user is not admin or manager."""
    if user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Admin access required",
        )


def assert_owns_resource(resource_user_id: int, current_user: User) -> None:
    """Raise HTTP 404 if the current user does not own the resource.

    Returns 404 (not 403) to avoid leaking information about resource existence.
    Admins can access any resource.
    """
    if current_user.role == "admin":
        return
    if resource_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
