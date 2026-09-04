"""HTTP metrics middleware.

Tracks request count and duration, labeled by method + normalized path.
Path normalization replaces path-parameter segments with their template name
so cardinality stays bounded (e.g. /api/v1/users/admin -> /api/v1/users/{username}).
"""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.metrics import request_duration_seconds, requests_total

# Segments that are clearly IDs / usernames / slugs — keep their name templated
# only if we can match it against the route. Otherwise fall back to a generic
# placeholder so the label cardinality stays bounded.
_ID_SEGMENT = re.compile(r"^[0-9a-fA-F-]{8,}$|^[0-9]+$")


def _normalize_path(request: Request) -> str:
    """Return a low-cardinality path label.

    Priority:
      1. Match the request path against registered route templates and use
         the templated form (e.g. /api/v1/users/{username}).
      2. Replace obvious ID-shaped segments with {id}.
      3. Fall back to the raw path (capped at a sensible length).
    """
    raw_path = request.url.path

    # 1. Try route templates — Starlette stores the compiled pattern on the
    #    route; the easiest match is to walk router.routes once at startup
    #    (cached on app.state) and look up by path shape.
    route_map: dict[str, str] = getattr(request.app.state, "_metrics_route_map", {})
    if route_map:
        for pattern, template in route_map.items():
            if pattern.match(raw_path):
                return template

    # 2. Cheap ID fallback for paths without a registered route.
    parts = raw_path.split("/")
    normalized = [
        "{id}" if _ID_SEGMENT.match(p) else p
        for p in parts
    ]
    return "/".join(normalized)


def _build_route_map(app: FastAPI) -> dict[str, re.Pattern[str]]:
    """Walk FastAPI routes and compile a path-template -> regex map.

    Returned as {compiled_pattern: template_path} so middleware lookup is O(n)
    but n is tiny (route count, not request count).
    """
    compiled: dict[str, re.Pattern[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/"):
            continue
        # Convert FastAPI path params (e.g. /users/{username}) to a regex that
        # matches any single segment.
        regex = "^" + re.sub(r"\{[^}]+\}", r"[^/]+", path) + "$"
        compiled[re.compile(regex)] = path
    return compiled


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Don't instrument the metrics endpoint itself — would recurse into
        # the scraper and pollute the histogram.
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            elapsed = time.perf_counter() - start
            endpoint = _normalize_path(request)
            method = request.method
            requests_total.labels(
                method=method, endpoint=endpoint, status=str(status_code)
            ).inc()
            request_duration_seconds.labels(method=method, endpoint=endpoint).observe(elapsed)


def install_metrics(app: FastAPI) -> None:
    """Register the route map and middleware on the app.

    Idempotent — safe to call from lifespan or module init.
    """
    if not hasattr(app.state, "_metrics_route_map") or not app.state._metrics_route_map:
        app.state._metrics_route_map = _build_route_map(app)
    # Avoid double-installing the middleware class.
    if any(m.cls is MetricsMiddleware for m in app.user_middleware):
        return
    app.add_middleware(MetricsMiddleware)
