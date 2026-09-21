"""Structured logging configuration for BAPENDA backend."""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import structlog
    structlog_available = True
except ImportError:
    structlog_available = False


# ─── JSON Formatter ───────────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = os.environ.get("APP_NAME", "local-ai-platform")
        self.service_version = os.environ.get("APP_VERSION", "1.0.0")

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "version": self.service_version,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from log call
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "funcName", "lineno", "asctime",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "exc_info", "exc_text",
                "stack_info", "vars", "tags",
            ):
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


# ─── Structured Logger Factory ────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Get a structured logger for a module.

    Usage:
        from app.logging import get_logger
        log = get_logger(__name__)
        log.info("user_login", username="admin", role="ADMIN")
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Use JSON formatter in production / non-TTY
    if os.environ.get("LOG_FORMAT", "json").lower() == "json" or not sys.stderr.isatty():
        formatter = JSONFormatter()
    else:
        # Human-readable in development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# ─── Audit Logger ─────────────────────────────────────────────────────

class AuditLogger:
    """Dedicated audit logger for security events.

    Logs are written to a separate file for easy monitoring.
    """

    def __init__(self):
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(logging.INFO)

        # File handler for audit logs
        audit_dir = os.environ.get("AUDIT_LOG_DIR", "./data/audit")
        os.makedirs(audit_dir, exist_ok=True)
        audit_file = os.path.join(audit_dir, "audit.log")

        file_handler = logging.FileHandler(audit_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JSONFormatter())
        self._logger.addHandler(file_handler)

    def log(
        self,
        action: str,
        user: str = "system",
        role: str = "",
        resource: str = "",
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit event.

        Args:
            action: What happened (e.g., "login", "query", "user_create")
            user: Username performing the action
            role: User's role
            resource: Resource being accessed
            status: success | failure | denied
            details: Additional context dict
        """
        self._logger.info(
            f"audit:{action}",
            extra={
                "action": action,
                "user": user,
                "role": role,
                "resource": resource,
                "status": status,
                "details": details or {},
            },
        )

    def log_login(self, username: str, role: str, status: str = "success") -> None:
        self.log("login", user=username, role=role, status=status)

    def log_query(self, username: str, role: str, intent: str, status: str = "success") -> None:
        self.log("query", user=username, role=role, resource="query", status=status,
                 details={"intent": intent})

    def log_user_change(self, username: str, action: str, target: str, status: str = "success") -> None:
        self.log("user_change", user=username, action=action, resource=target, status=status)


# Singleton audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience wrapper
audit_log = get_audit_logger()