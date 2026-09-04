"""FastAPI middleware for rate limiting and CORS."""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware as StarletteCORS
from typing import Dict, Callable
import time
from collections import defaultdict
import asyncio


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using sliding window."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests: Dict[str, list] = defaultdict(list)

    def _get_user_id(self, request: Request) -> str:
        """Get user identifier for rate limiting."""
        # Try to get from JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # In production, decode JWT to get user_id
            return f"token:{auth_header[7:20]}"
        # Fallback to IP
        return f"ip:{request.client.host}"

    def _is_rate_limited(self, user_id: str) -> bool:
        """Check if user is rate limited."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        # Clean old entries
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > minute_ago
        ]

        # Check limits
        if len(self.requests[user_id]) >= self.requests_per_minute:
            return True

        # Hour limit (cleanup and check)
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > hour_ago
        ]
        if len(self.requests[user_id]) >= self.requests_per_hour:
            return True

        return False

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        user_id = self._get_user_id(request)

        if self._is_rate_limited(user_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Rate limit exceeded. Please try again later.",
                    }
                },
            )

        # Record request
        self.requests[user_id].append(time.time())

        return await call_next(request)


class CORSMiddleware:
    """CORS middleware configuration."""

    def __init__(self, app):
        self.app = StarletteCORS(
            app=app,
            allow_origins=["http://localhost:3000", "https://app.bapenda.local"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
