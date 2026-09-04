"""Authentication - get_current_user reads app.state directly (no module-level globals)."""

from fastapi import Request, HTTPException, status
from typing import Dict, Any
import logging

from app.rbac.service import Role

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Dependency: validate Bearer token against AuthService on app.state.
    
    Reads token directly from Authorization header, validates against
    app.state.auth (set during lifespan startup).
    """
    auth = getattr(request.app.state, "auth", None)
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth service not initialized",
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]
    payload = auth.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("username") or payload.get("sub")
    role_str = payload.get("role")

    if not user_id or not role_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        role = Role(role_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = {
        "user_id": user_id,
        "role": role,
        "scope": payload.get("scope", {}),
        "token": token,
    }
    logger.debug(f"Authenticated: {user_id} role={role.value}")
    return user
