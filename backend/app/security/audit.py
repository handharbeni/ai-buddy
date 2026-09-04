"""Audit logging with hash chaining for tamper-evident audit trail."""

import json
import hashlib
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import os


@dataclass
class AuditEntry:
    """Single audit log entry."""
    id: str
    timestamp: str
    event_type: str
    user_id: str
    role: str
    action: str
    resource: str
    status: str  # success, failure, error
    metadata: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash of this entry."""
        # Create a deterministic string representation
        data = {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "role": self.role,
            "action": self.action,
            "resource": self.resource,
            "status": self.status,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
        }
        # Serialize deterministically
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "role": self.role,
            "action": self.action,
            "resource": self.resource,
            "status": self.status,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


class AuditLogger:
    """Audit logger with cryptographic hash chaining for tamper-evidence."""

    def __init__(self, log_file: str = "/var/log/bapenda/audit.log"):
        """Initialize the audit logger.

        Args:
            log_file: Path to the audit log file
        """
        self.log_file = log_file
        self._ensure_log_directory()
        self._previous_hash = self._get_last_hash()
        self._logger = logging.getLogger("audit")

    def _ensure_log_directory(self) -> None:
        """Ensure the log directory exists."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _get_last_hash(self) -> str:
        """Get the hash of the last entry in the log file."""
        if not os.path.exists(self.log_file):
            return ""

        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get("entry_hash", "")
        except Exception:
            pass
        return ""

    def log(
        self,
        event_type: str,
        user_id: str,
        role: str,
        action: str,
        resource: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Log an audit event with hash chaining.

        Args:
            event_type: Type of event (auth, query, tool_execution, admin, etc.)
            user_id: Authenticated user ID
            role: User's role
            action: Action performed (login, query, execute_tool, etc.)
            resource: Resource accessed (tax_revenue, tax_arrears, etc.)
            status: Outcome (success, failure, error)
            metadata: Additional metadata

        Returns:
            The created audit entry
        """
        entry = AuditEntry(
            id=f"audit_{int(time.time() * 1000000)}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type,
            user_id=user_id,
            role=role,
            action=action,
            resource=resource,
            status=status,
            metadata=metadata or {},
            previous_hash=self._previous_hash,
        )

        # Compute hash and store
        entry.entry_hash = entry.compute_hash()
        self._previous_hash = entry.entry_hash

        # Write to log file
        self._write_entry(entry)

        return entry

    def _write_entry(self, entry: AuditEntry) -> None:
        """Write an entry to the log file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logging.error(f"Failed to write audit log: {e}")

    def verify_chain(self) -> List[Dict[str, Any]]:
        """Verify the integrity of the audit log chain.

        Returns:
            List of verification results for each entry
        """
        if not os.path.exists(self.log_file):
            return []

        results = []
        previous_hash = ""

        try:
            with open(self.log_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    entry_data = json.loads(line.strip())
                    entry = AuditEntry(**entry_data)

                    # Verify chain
                    expected_hash = entry.compute_hash()
                    chain_valid = entry.previous_hash == previous_hash
                    hash_valid = entry.entry_hash == expected_hash

                    results.append({
                        "line": line_num,
                        "id": entry.id,
                        "chain_valid": chain_valid,
                        "hash_valid": hash_valid,
                        "expected_hash": expected_hash,
                        "actual_hash": entry.entry_hash,
                        "previous_hash": entry.previous_hash,
                    })

                    previous_hash = entry.entry_hash
        except Exception as e:
            logging.error(f"Failed to verify audit chain: {e}")
            results.append({"error": str(e)})

        return results


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def set_audit_logger(logger: AuditLogger) -> None:
    """Set a custom audit logger."""
    global _audit_logger
    _audit_logger = logger


def hash_chain(previous_hash: str, current_data: Dict[str, Any]) -> str:
    """Compute a hash chain value for linking audit entries."""
    data = {
        "previous_hash": previous_hash,
        "data": current_data,
    }
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()