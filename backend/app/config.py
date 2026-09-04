"""Local AI Data Intelligence Platform - Configuration Module.

Generic, project-agnostic configuration. Rename the project by setting:
  APP_NAME         — displayed title (default: "Local AI Platform")
  APP_TAGLINE      — short subtitle
  APP_DOMAIN       — e.g. "tax", "healthcare", "logistics" (used in docs)
  APP_INSTITUTION  — e.g. "BAPENDA Batam"

Handles multi-database authentication, LLM, RAG, and branding.
"""

import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from enum import Enum


class DBType(str, Enum):
    """Supported database types."""
    ORACLE = "oracle"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


# ─── Database Auth Models ────────────────────────────────────────────────────

class OracleAuth(BaseModel):
    """Oracle database authentication config."""
    name: str
    host: str
    port: int = 1521
    service_name: str
    user: str = "AI_READONLY"
    password: Optional[str] = None  # Loaded from password_env at runtime
    password_env: str = "ORACLE_PASSWORD"
    wallet_path: Optional[str] = None
    timeout_s: int = 30
    pool_min: int = 2
    pool_max: int = 10
    read_only: bool = True


class PostgreSQLAuth(BaseModel):
    """PostgreSQL database authentication config."""
    name: str
    host: str
    port: int = 5432
    database: str = "app_db"
    user: str = "ai_readonly"
    password: Optional[str] = None
    password_env: str = "POSTGRES_PASSWORD"
    timeout_s: int = 30
    pool_min: int = 2
    pool_max: int = 10
    read_only: bool = True


class MySQLAuth(BaseModel):
    """MySQL database authentication config."""
    name: str
    host: str
    port: int = 3306
    database: str = "app_db"
    user: str = "ai_readonly"
    password: Optional[str] = None
    password_env: str = "MYSQL_PASSWORD"
    timeout_s: int = 30
    pool_min: int = 2
    pool_max: int = 10
    read_only: bool = True


class LLMConfig(BaseModel):
    """LLM configuration."""
    backend: str = "ollama"
    base_url: str = "http://localhost:11434"
    model_name: str = "local-ai:latest"
    max_tokens: int = 4096
    temperature: float = 0.1
    top_p: float = 0.9
    timeout_s: int = 120


class RAGConfig(BaseModel):
    """RAG / Vector store configuration."""
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "regulations"
    embedding_model: str = "BAAI/bge-m3"
    top_k: int = 5


# ─── Application Branding (project-agnostic) ─────────────────────────────────

class AppBranding(BaseModel):
    """Customizable branding for the platform.

    Override via env vars: APP_NAME, APP_TAGLINE, APP_DOMAIN, APP_INSTITUTION.
    """
    name: str = "Local AI Platform"
    short_name: str = "LocalAI"
    tagline: str = "Internal AI for Data Intelligence"
    institution: str = ""
    domain: str = "data"
    version: str = "1.0.0"
    primary_color: str = "#6366F1"


# ─── Main Settings ───────────────────────────────────────────────────────────

class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # ── Branding (override to customize for any project) ──
    app_name: str = "Local AI Platform"
    app_short_name: str = "LocalAI"
    app_tagline: str = "Internal AI for Data Intelligence"
    app_institution: str = ""
    app_domain: str = "data"
    app_version: str = "1.0.0"

    # ── LLM ──
    llm_backend: str = "ollama"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "local-ai:latest"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
    llm_timeout: int = 120

    # ── RAG / Qdrant ──
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "regulations"
    rag_base_url: str = "http://localhost:8002"
    embedding_model: str = "BAAI/bge-m3"

    # ── Auth ──
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_min: int = 15
    jwt_refresh_expire_days: int = 7
    dev_mode: bool = True  # Use hardcoded dev users; set to False in production

    # ── OIDC (optional) ──
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None

    # ── Server ──
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]

    # ── Database (overridable via env) ──
    use_mock_db: bool = False  # Force mock adapters

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        extra = "ignore"


def get_llm_config() -> LLMConfig:
    """Get LLM configuration from environment."""
    return LLMConfig(
        backend=settings.llm_backend,
        base_url=settings.llm_base_url,
        model_name=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        timeout_s=settings.llm_timeout,
    )


def get_branding() -> AppBranding:
    """Get application branding (customizable per deployment)."""
    return AppBranding(
        name=settings.app_name,
        short_name=settings.app_short_name,
        tagline=settings.app_tagline,
        institution=settings.app_institution,
        domain=settings.app_domain,
        version=settings.app_version,
    )


# ─── Database Connection Registry ────────────────────────────────────────────
#
# Add your databases here. Each entry reads password from an env var.
# To add a new database, append to the appropriate dict.
#
# Example for a healthcare project:
#   "primary": {
#       "name": "primary",
#       "host": "pgrx.hospital.go.id",
#       "user": "ai_readonly",
#       "password_env": "HEALTHCARE_PG_PASSWORD",
#   }
#
# To disable a database, set its env vars to empty.

def _build_oracle_configs() -> Dict[str, Dict]:
    """Build Oracle DB configs from env. Auto-detects ORACLE_*_HOST patterns."""
    configs: Dict[str, Dict] = {}
    # Pattern: ORACLE_<NAME>_HOST → creates entry "name"
    seen_names: set = set()
    for key in os.environ:
        if key.startswith("ORACLE_") and key.endswith("_HOST"):
            # e.g. ORACLE_BATAMAI_HOST → BATAMAI
            name = key[len("ORACLE_"):-len("_HOST")].lower()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            prefix = f"ORACLE_{name.upper()}"
            host = os.environ.get(f"{prefix}_HOST", "").strip()
            if not host:
                continue
            configs[name] = {
                "name": name,
                "host": host,
                "port": int(os.environ.get(f"{prefix}_PORT", "1521")),
                "service_name": os.environ.get(f"{prefix}_SERVICE", os.environ.get(f"{prefix}_SID", "")),
                "user": os.environ.get(f"{prefix}_USER", "ai_readonly"),
                "password": os.environ.get(f"{prefix}_PASSWORD", ""),
                "password_env": f"{prefix}_PASSWORD",
                "timeout_s": int(os.environ.get(f"{prefix}_TIMEOUT", "30")),
                "read_only": os.environ.get(f"{prefix}_READONLY", "true").lower() == "true",
            }
    return configs


def _build_postgres_configs() -> Dict[str, Dict]:
    """Build PostgreSQL configs from env."""
    configs: Dict[str, Dict] = {}
    seen_names: set = set()
    for key in os.environ:
        if key.startswith("POSTGRES_") and key.endswith("_HOST"):
            name = key[len("POSTGRES_"):-len("_HOST")].lower()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            prefix = f"POSTGRES_{name.upper()}"
            host = os.environ.get(f"{prefix}_HOST", "").strip()
            if not host:
                continue
            configs[name] = {
                "name": name,
                "host": host,
                "port": int(os.environ.get(f"{prefix}_PORT", "5432")),
                "database": os.environ.get(f"{prefix}_DB", "app_db"),
                "user": os.environ.get(f"{prefix}_USER", "ai_readonly"),
                "password": os.environ.get(f"{prefix}_PASSWORD", ""),
                "password_env": f"{prefix}_PASSWORD",
                "timeout_s": int(os.environ.get(f"{prefix}_TIMEOUT", "30")),
                "read_only": os.environ.get(f"{prefix}_READONLY", "true").lower() == "true",
            }
    return configs


def _build_mysql_configs() -> Dict[str, Dict]:
    """Build MySQL configs from env."""
    configs: Dict[str, Dict] = {}
    seen_names: set = set()
    for key in os.environ:
        if key.startswith("MYSQL_") and key.endswith("_HOST"):
            name = key[len("MYSQL_"):-len("_HOST")].lower()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            prefix = f"MYSQL_{name.upper()}"
            host = os.environ.get(f"{prefix}_HOST", "").strip()
            if not host:
                continue
            configs[name] = {
                "name": name,
                "host": host,
                "port": int(os.environ.get(f"{prefix}_PORT", "3306")),
                "database": os.environ.get(f"{prefix}_DB", "app_db"),
                "user": os.environ.get(f"{prefix}_USER", "ai_readonly"),
                "password": os.environ.get(f"{prefix}_PASSWORD", ""),
                "password_env": f"{prefix}_PASSWORD",
                "timeout_s": int(os.environ.get(f"{prefix}_TIMEOUT", "30")),
                "read_only": os.environ.get(f"{prefix}_READONLY", "true").lower() == "true",
            }
    return configs


# Registry — auto-built from env. Add a new DB by setting ORACLE_FOO_HOST etc.
DATABASE_CONFIGS: Dict[str, Dict[str, Dict]] = {
    "oracle": _build_oracle_configs(),
    "postgresql": _build_postgres_configs(),
    "mysql": _build_mysql_configs(),
}


def get_db_config(db_type: str, name: str) -> Optional[Dict]:
    """Get a database configuration by type and name.

    Usage:
        cfg = get_db_config("oracle", "batamai")
        if cfg:
            password = cfg.get("password") or os.environ[cfg["password_env"]]
    """
    return DATABASE_CONFIGS.get(db_type, {}).get(name)


def get_all_db_configs(db_type: str) -> Dict[str, Dict]:
    """Get all database configurations of a given type."""
    return DATABASE_CONFIGS.get(db_type, {})


# ─── Singleton ───────────────────────────────────────────────────────────────

settings = Settings()
