"""Secrets management for BAPENDA Local AI Platform.

Provides secure access to secrets with caching, rotation support,
and audit logging. Supports multiple backends: environment variables,
Docker secrets, and external vaults.
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manage secrets from multiple sources with caching and validation."""

    def __init__(self, backend: str = "auto"):
        """Initialize secrets manager.

        Args:
            backend: Secret source. Options: 'env', 'docker', 'vault', 'auto'
        """
        self.backend = backend
        self._cache: Dict[str, str] = {}
        self._loaded = False

    def _detect_backend(self) -> str:
        """Auto-detect the best available backend."""
        # Check for Docker secrets first (production)
        if os.path.exists("/run/secrets"):
            return "docker"
        # Check for environment variables
        if os.environ.get("BAPENDA_ENVIRONMENT") == "production":
            return "env"
        # Default to environment variables
        return "env"

    def _load_docker_secret(self, name: str) -> Optional[str]:
        """Load a secret from Docker secrets."""
        path = Path(f"/run/secrets/{name}")
        if path.exists():
            try:
                return path.read_text().strip()
            except Exception as e:
                logger.error(f"Failed to read secret {name}: {e}")
        return None

    def get(self, name: str, default: Optional[str] = None) -> str:
        """Get a secret value.

        Args:
            name: Secret name
            default: Default value if secret not found

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found and no default provided
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        # Load from appropriate backend
        value = None
        backend = self.backend if self.backend != "auto" else self._detect_backend()

        if backend == "docker":
            value = self._load_docker_secret(name)
        elif backend == "env":
            value = os.environ.get(name)
        else:
            # Try all backends
            value = self._load_docker_secret(name)
            if value is None:
                value = os.environ.get(name)

        if value is None:
            if default is not None:
                value = default
            else:
                raise ValueError(f"Secret '{name}' not found and no default provided")

        # Cache the value
        self._cache[name] = value
        return value

    def get_hash(self, name: str) -> str:
        """Get the SHA-256 hash of a secret (for verification)."""
        value = self.get(name)
        return hashlib.sha256(value.encode()).hexdigest()

    def refresh(self) -> None:
        """Clear the cache to force reload from backend."""
        self._cache.clear()
        logger.info("Secret cache refreshed")


# Global secrets manager instance
_secrets_manager = SecretsManager()


def get_secret(name: str, default: Optional[str] = None) -> str:
    """Get a secret value using the global secrets manager."""
    return _secrets_manager.get(name, default)


def set_secret_manager(manager: SecretsManager) -> None:
    """Set a custom secrets manager instance."""
    global _secrets_manager
    _secrets_manager = manager


def refresh_secrets() -> None:
    """Refresh all cached secrets."""
    _secrets_manager.refresh()