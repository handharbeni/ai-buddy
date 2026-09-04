"""API v1 package."""
from app.api.v1.auth import router as auth_router
from app.api.v1.query import router as query_router
from app.api.v1.config import router as config_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.users import router as users_router

__all__ = [
    "auth_router",
    "query_router",
    "config_router",
    "conversations_router",
    "users_router",
]
