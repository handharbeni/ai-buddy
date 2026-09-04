"""Authentication service — Local AI Data Intelligence Platform.

Provides dev-mode login with hardcoded users and simple JWT token generation/validation.
Users are seeded into SQLite on first startup. New users via the API persist there.

Production: replace verify_access_token to query the database (e.g. Oracle, PostgreSQL).
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT secret — overridden by JWT_SECRET env var in production
SECRET_KEY = os.environ.get("JWT_SECRET", "bapenda-dev-secret-change-me-in-prod-2026")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_EXPIRE_MIN", "15"))

# Password hashing context — pbkdf2_sha256 avoids bcrypt 72-byte limit
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Default scope for new users
DEFAULT_SCOPE = {
    "regions": ["ALL"],
    "tax_types": ["ALL"],
    "departments": ["ALL"],
    "own_taxpayers": False,
}


def _dev_user_dict(username: str, password: str, role: str, display_name: str) -> Dict[str, Any]:
    return {
        "username": username,
        "hashed_password": pwd_context.hash(password),
        "role": role,
        "user_id": username,
        "scope": dict(DEFAULT_SCOPE),
        "display_name": display_name,
    }


# Dev mode users (hardcoded; also seeded into SQLite on first startup)
DEV_USERS: Dict[str, Dict[str, Any]] = {
    "admin": _dev_user_dict("admin", "admin123", "ADMIN", "Admin"),
    "supervisor": _dev_user_dict("supervisor", "super123", "SUPERVISOR", "Supervisor"),
    "analyst": _dev_user_dict("analyst", "analyst123", "ANALYST", "Analyst"),
    "staff": _dev_user_dict("staff", "staff123", "STAFF", "Staff"),
}


def _seed_dev_users_to_db() -> None:
    """On first startup, copy DEV_USERS into SQLite. Idempotent."""
    try:
        from app.storage import get_user, create_user
        for u in DEV_USERS.values():
            if get_user(u["username"]) is None:
                create_user(
                    username=u["username"],
                    password_hash=u["hashed_password"],
                    role=u["role"],
                    user_id=u["user_id"],
                    scope=u["scope"],
                    display_name=u.get("display_name", u["username"].title()),
                )
    except Exception:
        # SQLite may not be available; fall back to in-memory DEV_USERS
        pass


# ─── Helpers ────────────────────────────────────────────────────────────────

def _load_user(username: str) -> Optional[Dict[str, Any]]:
    """Load user from SQLite first, fall back to in-memory DEV_USERS."""
    try:
        from app.storage import get_user as _db_get
        u = _db_get(username)
        if u:
            return {
                "username": u["username"],
                "hashed_password": u["password_hash"],
                "role": u["role"],
                "user_id": u["user_id"],
                "scope": json.loads(u["scope_json"]) if u.get("scope_json") else {},
                "display_name": u.get("display_name") or u["username"].title(),
                "is_active": bool(u.get("is_active", 1)),
            }
    except Exception:
        pass
    return DEV_USERS.get(username)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user from SQLite (or DEV_USERS fallback)."""
    user = _load_user(username)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    # Strip password before returning
    return {
        "username": user["username"],
        "role": user["role"],
        "user_id": user["user_id"],
        "scope": user["scope"],
        "display_name": user.get("display_name"),
    }


def create_access_token(data: Dict[str, Any],
                         expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT and return user data from SQLite/DEV_USERS."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = _load_user(username)
        if user is None:
            return None
        return {
            "sub": user["username"],
            "username": user["username"],
            "role": user["role"],
            "user_id": user["user_id"],
            "scope": user["scope"],
        }
    except JWTError:
        return None


# ─── AuthService class (used by main.py lifespan) ──────────────────────────

class AuthService:
    """Auth service wrapper."""

    def __init__(self, db_adapters: dict | None = None):
        self._db = db_adapters or {}
        # Backward-compat: USERS points to in-memory DEV_USERS for any caller
        self.USERS = DEV_USERS
        # Seed dev users into SQLite (idempotent)
        _seed_dev_users_to_db()

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        return verify_access_token(token)

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        return authenticate_user(username, password)

    def create_access_token(self, data: Dict[str, Any],
                            expires_delta: Optional[timedelta] = None) -> str:
        return create_access_token(data, expires_delta)
