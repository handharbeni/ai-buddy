"""Auth dependency for FastAPI routes.

Uses Depends() pattern instead of middleware for reliable auth.
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from app.auth.service import AuthService
from app.rbac.service import RBACService, Role

logger = logging.getLogger(__name__)

# Bearer token scheme for JWT authentication
security_scheme = HTTPBearer(auto_error=False)

# Store services globally (set during app startup)
_auth_service: Optional[AuthService] = None
_rbac_service: Optional[RBACService] = None


def set_auth_services(auth_service: AuthService, rbac_service: RBACService):
    """Set auth services (called during app startup)."""
    global _auth_service, _rbac_service
    _auth_service = auth_service
    _rbac_service = rbac_service


def set_rbac_service(rbac_service: RBACService):
    """Set the RBAC service only."""
    global _rbac_service
    _rbac_service = rbac_service


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> dict:
    """FastAPI dependency to extract and validate the current user from JWT.

    Returns user dict with user_id, role, scope, token.
    Raises 401 if token is missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = _auth_service.verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    role_str = payload.get("role")

    if not user_id or not role_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        role = Role(role_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role",
        )

    return {
        "user_id": user_id,
        "role": role,
        "scope": payload.get("scope", {}),
        "token": token,
    }


def get_rbac_service() -> RBACService:
    """Get the RBAC service instance."""
    if _rbac_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RBAC service not initialized",
        )
    return _rbac_service
