"""SQLite storage for conversations and users.

Default location: ./data/app.db (relative to backend working dir).
Override with: STORAGE_DB_PATH=/path/to/db
"""
import os
import sqlite3
import json
import logging
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("STORAGE_DB_PATH", "./data/app.db")

# Thread-local connection
_local = threading.local()


def _ensure_data_dir(path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)


def get_db_path() -> str:
    return os.environ.get("STORAGE_DB_PATH", DEFAULT_DB_PATH)


def get_connection() -> sqlite3.Connection:
    """Get a thread-local connection to SQLite."""
    if not hasattr(_local, "conn") or _local.conn is None:
        path = get_db_path()
        _ensure_data_dir(path)
        _local.conn = sqlite3.connect(path, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _init_schema(_local.conn)
    return _local.conn


@contextmanager
def get_db():
    """Context manager for DB operations."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _init_schema(conn: sqlite3.Connection) -> None:
    """Initialize database schema."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            user_id TEXT NOT NULL,
            scope_json TEXT NOT NULL,
            display_name TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_conv_user
            ON conversations(user_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata_json TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_msg_conv
            ON messages(conversation_id, created_at);

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_id TEXT,
            role TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            request_id TEXT,
            status TEXT,
            details_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_time
            ON audit_log(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_user
            ON audit_log(user_id, timestamp DESC);
    """)
    conn.commit()


# ─── User CRUD ─────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, role: str,
                user_id: str, scope: Dict, display_name: str = "") -> None:
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        db.execute("""
            INSERT INTO users (username, password_hash, role, user_id, scope_json,
                               display_name, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (username, password_hash, role, user_id,
              json.dumps(scope), display_name or username.title(), now, now))


def update_user(username: str, **fields) -> bool:
    if not fields:
        return False
    allowed = {"role", "display_name", "is_active", "scope_json", "password_hash"}
    sets = []
    values = []
    for k, v in fields.items():
        if k in allowed:
            if k == "scope" and isinstance(v, dict):
                sets.append("scope_json = ?")
                values.append(json.dumps(v))
            else:
                sets.append(f"{k} = ?")
                values.append(v)
    if not sets:
        return False
    sets.append("updated_at = ?")
    values.append(datetime.utcnow().isoformat())
    values.append(username)
    with get_db() as db:
        cur = db.execute(f"UPDATE users SET {', '.join(sets)} WHERE username = ?", values)
        return cur.rowcount > 0


def delete_user(username: str) -> bool:
    with get_db() as db:
        cur = db.execute("DELETE FROM users WHERE username = ?", (username,))
        return cur.rowcount > 0


def get_user(username: str) -> Optional[Dict]:
    with get_db() as db:
        row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return dict(row)
    return None


def list_users() -> List[Dict]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM users ORDER BY username").fetchall()
    return [dict(r) for r in rows]


# ─── Conversation CRUD ─────────────────────────────────────────────────────

def create_conversation(conv_id: str, user_id: str, title: str) -> None:
    now = int(datetime.utcnow().timestamp() * 1000)
    with get_db() as db:
        db.execute("""
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (conv_id, user_id, title, now, now))


def update_conversation(conv_id: str, **fields) -> bool:
    if not fields:
        return False
    allowed = {"title", "updated_at"}
    sets = []
    values = []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            values.append(v)
    if not sets:
        return False
    values.append(conv_id)
    with get_db() as db:
        cur = db.execute(f"UPDATE conversations SET {', '.join(sets)} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_conversation(conv_id: str) -> bool:
    with get_db() as db:
        cur = db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        return cur.rowcount > 0


def list_conversations(user_id: str, limit: int = 100) -> List[Dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_conversation_messages(conv_id: str) -> List[Dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conv_id,)).fetchall()
    return [dict(r) for r in rows]


# ─── Message CRUD ──────────────────────────────────────────────────────────

def add_message(msg_id: str, conversation_id: str, role: str,
                content: str, metadata: Optional[Dict] = None) -> None:
    now = int(datetime.utcnow().timestamp() * 1000)
    meta_json = json.dumps(metadata) if metadata else None
    with get_db() as db:
        db.execute("""
            INSERT INTO messages (id, conversation_id, role, content, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (msg_id, conversation_id, role, content, meta_json, now))
        # Update conversation's updated_at
        db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?",
                   (now, conversation_id))


def clear_conversation_messages(conv_id: str) -> None:
    """Clear all messages in a conversation (keep the conversation)."""
    with get_db() as db:
        db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))


# ─── Audit Log ─────────────────────────────────────────────────────────────

def log_audit(user_id: str, role: str, action: str, resource: str = "",
              request_id: str = "", status: str = "success",
              details: Optional[Dict] = None) -> None:
    """Append-only audit log entry."""
    now = datetime.utcnow().isoformat()
    details_json = json.dumps(details) if details else None
    try:
        with get_db() as db:
            db.execute("""
                INSERT INTO audit_log (timestamp, user_id, role, action, resource,
                                       request_id, status, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, user_id, role, action, resource, request_id, status, details_json))
    except Exception as e:
        logger.warning(f"audit log write failed: {e}")


def list_audit_logs(limit: int = 100, user_id: Optional[str] = None) -> List[Dict]:
    """Read audit log (admin only — enforced at endpoint)."""
    with get_db() as db:
        if user_id:
            rows = db.execute("""
                SELECT * FROM audit_log WHERE user_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (user_id, limit)).fetchall()
        else:
            rows = db.execute("""
                SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ─── Health check ──────────────────────────────────────────────────────────

def health_check() -> bool:
    """Test DB connection."""
    try:
        with get_db() as db:
            db.execute("SELECT 1").fetchone()
        return True
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        return False
