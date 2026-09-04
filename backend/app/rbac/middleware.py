"""RBAC middleware for permission checking."""

from fastapi import Request, HTTPException, status
from typing import Optional
import logging

from app.rbac.service import RBACService, Role, Resource, Action

logger = logging.getLogger(__name__)


class RBACMiddleware:
    """Middleware to enforce role-based access control."""

    def __init__(self, rbac_service: RBACService):
        self.rbac_service = rbac_service

    async def __call__(self, request: Request, call_next):
        public_paths = [
            "/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
        ]
        if request.url.path in public_paths:
            return await call_next(request)

        if not hasattr(request.state, "user") or not request.state.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = request.state.user
        role = user.get("role")
        if not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication",
                headers={"WWW-Authenticate": "Bearer"},
            )

        required_resource = getattr(request.state, "required_resource", None)
        required_action = getattr(request.state, "required_action", None)

        if required_resource and required_action:
            try:
                resource_enum = Resource(required_resource)
                action_enum = Action(required_action)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid permission configuration",
                )

            if not self.rbac_service.check_permission(role, resource_enum, action_enum):
                logger.warning(
                    f"Permission denied: user={user.get('user_id')} "
                    f"role={role} attempted {action_enum.value} on {resource_enum.value}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {role.value} not authorized for this action",
                )

        return await call_next(request)