"""SQLite backup utility for BAPENDA backend."""

import os
import shutil
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_backup_dir() -> str:
    """Get the backup directory path."""
    base_dir = os.environ.get("STORAGE_DB_PATH", "./data/app.db")
    backup_dir = os.environ.get(
        "DB_BACKUP_DIR", os.path.join(os.path.dirname(base_dir), "backups")
    )
    return backup_dir


def get_db_path() -> str:
    """Get the current database path."""
    return os.environ.get("STORAGE_DB_PATH", "./data/app.db")


def backup_db(backup_name: Optional[str] = None) -> Optional[str]:
    """
    Create a backup of the SQLite database.

    Args:
        backup_name: Optional custom name. If not provided, uses timestamp.

    Returns:
        Path to the backup file, or None if backup failed.
    """
    db_path = get_db_path()
    backup_dir = get_backup_dir()

    # Check if DB exists
    if not os.path.exists(db_path):
        logger.warning(f"Database not found at {db_path}, skipping backup")
        return None

    # Create backup directory if needed
    os.makedirs(backup_dir, exist_ok=True)

    # Generate backup filename
    if backup_name is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"app_{timestamp}.db"

    backup_path = os.path.join(backup_dir, backup_name)

    try:
        # Copy the SQLite database file
        shutil.copy2(db_path, backup_path)

        # Verify the backup
        import sqlite3
        conn = sqlite3.connect(backup_path)
        conn.execute("SELECT count(*) FROM users")
        conn.execute("SELECT count(*) FROM conversations")
        conn.close()

        logger.info(f"Database backed up to {backup_path}")
        return backup_path

    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        # Clean up partial backup
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return None


def list_backups() -> list[Dict[str, Any]]:
    """
    List all available database backups.

    Returns:
        List of backup info dicts with filename, size, and timestamp.
    """
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return []

    backups = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath) and fname.endswith(".db"):
            stat = os.stat(fpath)
            backups.append({
                "filename": fname,
                "path": fpath,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "age_hours": (datetime.now().timestamp() - stat.st_mtime) / 3600,
            })

    return backups


def cleanup_old_backups(days: int = 30) -> int:
    """
    Remove backups older than specified days.

    Args:
        days: Remove backups older than this many days.

    Returns:
        Number of backups removed.
    """
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return 0

    removed = 0
    cutoff = datetime.now().timestamp() - (days * 24 * 3600)

    for fname in os.listdir(backup_dir):
        fpath = os.path.join(backup_dir, fname)
        if os.path.isfile(fpath) and fname.endswith(".db"):
            stat = os.stat(fpath)
            if stat.st_mtime < cutoff:
                os.remove(fpath)
                removed += 1
                logger.info(f"Removed old backup: {fname}")

    return removed


def verify_backup(backup_path: str) -> bool:
    """
    Verify a database backup is valid and not corrupted.

    Args:
        backup_path: Path to the backup file.

    Returns:
        True if backup is valid, False otherwise.
    """
    if not os.path.exists(backup_path):
        return False

    try:
        import sqlite3
        conn = sqlite3.connect(backup_path)
        # Check required tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {"users", "conversations", "messages", "audit_log"}
        if not required_tables.issubset(tables):
            logger.warning(f"Backup missing required tables: {required_tables - tables}")
            return False

        # Check data integrity
        cursor.execute("SELECT count(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM conversations")
        conv_count = cursor.fetchone()[0]

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        return False


# Convenience function for cron/CLI usage
def backup_now(backup_name: Optional[str] = None) -> Optional[str]:
    """
    Run backup immediately.

    Args:
        backup_name: Optional custom name.

    Returns:
        Path to backup file.
    """
    return backup_db(backup_name)