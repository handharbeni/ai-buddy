"""User management API — admin only.

GET    /api/v1/users                  — list all users
POST   /api/v1/users                  — create a new user (admin)
GET    /api/v1/users/{username}       — get one user
PATCH  /api/v1/users/{username}       — update role/scope/active (admin)
DELETE /api/v1/users/{username}       — delete user (admin; cannot delete self)
POST   /api/v1/users/{username}/reset-password — admin resets a user's password
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json

from app.auth import get_current_user
from app.auth.service import get_password_hash, verify_password
from app.storage import list_users, get_user, create_user, update_user, delete_user
from app.rbac.service import Role
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


def _require_admin(user: dict) -> None:
    role = user.get("role")
    if isinstance(role, Role):
        role = role.value
    if role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(..., min_length=4, max_length=128)
    role: str = Field(..., pattern=r"^(ADMIN|SUPERVISOR|ANALYST|STAFF)$")
    display_name: str = Field("", max_length=128)
    scope: Optional[Dict[str, Any]] = None


class UserUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern=r"^(ADMIN|SUPERVISOR|ANALYST|STAFF)$")
    display_name: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None
    scope: Optional[Dict[str, Any]] = None


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=128)


class UserOut(BaseModel):
    username: str
    user_id: str
    role: str
    display_name: str
    scope: Dict[str, Any]
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _serialize_user(u: Dict[str, Any]) -> UserOut:
    return UserOut(
        username=u["username"],
        user_id=u.get("user_id", u["username"]),
        role=u["role"],
        display_name=u.get("display_name") or u["username"].title(),
        scope=json.loads(u["scope_json"]) if u.get("scope_json") else {},
        is_active=bool(u.get("is_active", 1)),
        created_at=u.get("created_at"),
        updated_at=u.get("updated_at"),
    )


@router.get("", response_model=List[UserOut])
async def list_all_users(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return [_serialize_user(u) for u in list_users()]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_new_user(body: UserCreate, user: dict = Depends(get_current_user)):
    _require_admin(user)
    if get_user(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User '{body.username}' already exists",
        )
    from app.auth.service import DEFAULT_SCOPE
    scope = body.scope or dict(DEFAULT_SCOPE)
    create_user(
        username=body.username,
        password_hash=get_password_hash(body.password),
        role=body.role,
        user_id=body.username,
        scope=scope,
        display_name=body.display_name or body.username.title(),
    )
    return _serialize_user(get_user(body.username))


@router.get("/{username}", response_model=UserOut)
async def get_one_user(username: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    u = get_user(username)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )
    return _serialize_user(u)


@router.patch("/{username}", response_model=UserOut)
async def update_one_user(username: str, body: UserUpdate,
                          user: dict = Depends(get_current_user)):
    _require_admin(user)
    u = get_user(username)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )
    if username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify the admin user",
        )
    fields = {}
    if body.role is not None:
        fields["role"] = body.role
    if body.display_name is not None:
        fields["display_name"] = body.display_name
    if body.is_active is not None:
        fields["is_active"] = 1 if body.is_active else 0
    if body.scope is not None:
        fields["scope_json"] = json.dumps(body.scope)
    if fields:
        update_user(username, **fields)
    return _serialize_user(get_user(username))


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one_user(username: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    # Prevent self-delete
    if user.get("user_id") == username or user.get("username") == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    if not get_user(username):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )
    delete_user(username)
    return None


@router.post("/{username}/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(username: str, body: PasswordReset,
                          user: dict = Depends(get_current_user)):
    _require_admin(user)
    u = get_user(username)
    if not u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )
    update_user(username, password_hash=get_password_hash(body.new_password))
    return {"message": f"Password reset for {username}"}
