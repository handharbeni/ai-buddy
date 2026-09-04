"""API endpoints package."""

from app.api.v1.auth import router as auth_router
from app.api.v1.query import router as query_router

__all__ = ["auth_router", "query_router"]