"""Prometheus metrics registry for the BAPENDA backend.

All metric singletons live here so any module can `from app.metrics import <name>`
without re-creating the collectors (which would double-count under multiprocess).
"""

from prometheus_client import Counter, Gauge, Histogram

# HTTP layer -----------------------------------------------------------------
requests_total = Counter(
    "requests_total",
    "Total HTTP requests handled.",
    ["method", "endpoint", "status"],
)

request_duration_seconds = Histogram(
    "request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
)

# LLM layer ------------------------------------------------------------------
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API calls.",
    ["status", "model"],
)

llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM call latency in seconds.",
    ["model"],
)

# Database health ------------------------------------------------------------
# Spec calls it a "Counter" but the semantics (current connection state) are
# gauge: 1 = up, 0 = down. Counter would only ever increase — wrong fit.
db_connection_status = Gauge(
    "db_connection_status",
    "Database connection status (1 = up, 0 = down).",
    ["db_type", "db_name"],
)

# Security -------------------------------------------------------------------
prompt_injection_detected_total = Counter(
    "prompt_injection_detected_total",
    "Total prompt-injection attempts detected.",
)

# Domain events --------------------------------------------------------------
conversations_total = Counter(
    "conversations_total",
    "Conversation lifecycle events.",
    ["action"],  # create | delete
)

users_total = Counter(
    "users_total",
    "User lifecycle events.",
    ["action"],  # create | delete | login
)

__all__ = [
    "requests_total",
    "request_duration_seconds",
    "llm_requests_total",
    "llm_latency_seconds",
    "db_connection_status",
    "prompt_injection_detected_total",
    "conversations_total",
    "users_total",
]
