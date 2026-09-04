"""RBAC middleware for permission checking."""

import logging
from typing import Optional
from fastapi import Request, HTTPException, status

from app.rbac.service import RBACService, Role, Resource, Action

logger = logging.getLogger(__name__)

# Module-level service (set during startup)
_rbac_service: Optional[RBACService] = None


def set_rbac_service(rbac_service: RBACService):
    """Set RBAC service (called during app startup)."""
    global _rbac_service
    _rbac_service = rbac_service


async def rbac_middleware(request: Request, call_next):
    """Function-based RBAC middleware."""
    public_paths = [
        "/health", "/", "/docs", "/redoc", "/openapi.json",
        "/api/v1/auth/login", "/api/v1/auth/refresh",
    ]
    if request.url.path in public_paths:
        return await call_next(request)

    if not hasattr(request.state, 'user') or not request.state.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = request.state.user
    role = user.get('role')
    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Bearer"},
        )

    required_resource = getattr(request.state, 'required_resource', None)
    required_action = getattr(request.state, 'required_action', None)

    if required_resource and required_action and _rbac_service:
        try:
            resource_enum = Resource(required_resource)
            action_enum = Action(required_action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid permission configuration",
            )

        if not _rbac_service.check_permission(role, resource_enum, action_enum):
            logger.warning(
                f"Permission denied: user {user.get('user_id')} "
                f"with role {role.value if hasattr(role, 'value') else role} "
                f"attempted {action_enum.value} on {resource_enum.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role not authorized for this action",
            )

    return await call_next(request)
