"""
RBAC enforcement.

Two layers:
1. Coarse-grained: `require_roles(...)` as a route dependency - fast fail
   before any business logic runs.
2. Fine-grained: `Permission` checks inside services for record-level
   rules (e.g. "user can only edit their own conversations") that role
   membership alone can't express.

Roles come from the validated Azure AD token's `roles` claim (App Roles
configured on the Azure AD App Registration) - single source of truth,
no separate roles table to keep in sync for v1's single-tenant model.
"""
from enum import StrEnum

from fastapi import Depends, HTTPException, status

from text_to_sql_agent.app.core.security import CurrentUser, get_current_user


class Role(StrEnum):
    ADMIN = "Admin"
    AGENT_OPERATOR = "AgentOperator"
    ANALYST = "Analyst"
    VIEWER = "Viewer"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.ANALYST: 1,
    Role.AGENT_OPERATOR: 2,
    Role.ADMIN: 3,
}


def require_roles(*allowed: Role):
    """
    Route-level dependency: `Depends(require_roles(Role.ADMIN, Role.AGENT_OPERATOR))`
    Grants access if the user holds ANY of the listed roles.
    """

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user_roles = {r for r in user.roles if r in Role._value2member_map_}
        if not user_roles.intersection({r.value for r in allowed}):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires one of roles: {[r.value for r in allowed]}",
            )
        return user

    return _dependency


def require_min_role(minimum: Role):
    """Route-level dependency using the role hierarchy (e.g. Analyst+ )."""

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        user_level = max(
            (ROLE_HIERARCHY[Role(r)] for r in user.roles if r in Role._value2member_map_),
            default=-1,
        )
        if user_level < ROLE_HIERARCHY[minimum]:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Requires role {minimum.value} or higher"
            )
        return user

    return _dependency


def has_role(user: CurrentUser, role: Role) -> bool:
    return role.value in user.roles


class PermissionDenied(Exception):
    """Raised inside services for record-level RBAC failures; mapped to 403 by exception handler."""
