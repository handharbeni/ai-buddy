"""Auth API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.auth.service import AuthService, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.auth import get_current_user

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    """Simple JSON login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str
    expires_in: int


class UserInfo(BaseModel):
    """Current user info."""
    user_id: str
    role: str
    scope: Dict[str, Any] = {}


# Singleton instance (set during app startup)
_auth_service: Optional[AuthService] = None


def set_auth_service(service: AuthService):
    """Set the auth service singleton."""
    global _auth_service
    _auth_service = service


def get_auth_service() -> AuthService:
    """Dependency to get the auth service."""
    if _auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not initialized",
        )
    return _auth_service


@router.post("/login", response_model=TokenResponse)
async def login_json(request: LoginRequest):
    """Login with JSON body (preferred for frontend)."""
    session = _auth_service.authenticate_user(request.username, request.password)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = create_access_token(data={
        "sub": session["username"],
        "role": session["role"],
        "scope": session["scope"],
    })
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login/oauth", response_model=TokenResponse)
async def login_oauth(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 form login (for Swagger UI)."""
    session = _auth_service.authenticate_user(form_data.username, form_data.password)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = create_access_token(data={
        "sub": session["username"],
        "role": session["role"],
        "scope": session["scope"],
    })
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserInfo(
        user_id=user.get("user_id"),
        role=user.get("role").value if hasattr(user.get("role"), "value") else str(user.get("role")),
        scope=user.get("scope", {}),
    )


@router.get("/users")
async def list_users():
    """List available dev users (no passwords shown)."""
    if _auth_service is None:
        return {"users": []}
    users = []
    for username, info in _auth_service.USERS.items():
        users.append({
            "username": username,
            "user_id": info["user_id"],
            "role": info["role"].value if hasattr(info["role"], "value") else str(info["role"]),
            "display_name": info.get("display_name", username.title()),
        })
    return {"users": users}
