"""Database adapters for the BAPENDA Local AI Platform.

This module provides read-only database adapters for Oracle, PostgreSQL, and MySQL.
All adapters enforce security controls:
- Read-only access via AI_READONLY user
- Row-level security via scope filters
- Timeout enforcement (default 30 seconds)
- Row limit enforcement (default 1000 rows)
- Parameterized queries only

Usage:
    from app.db import OracleAdapter, PostgreSQLAdapter, MySQLAdapter, ScopeFilter
    
    # Create adapter
    adapter = OracleAdapter(dsn=dsn, username="AI_READONLY", password=pwd)
    
    # Query with scope
    scope = ScopeFilter(user_id="123", role="STAFF", regions=["3201"])
    result = await adapter.execute_query(
        "SELECT * FROM V_TAX_REVENUE_SCOPE WHERE period = :period",
        params={"period": "2025-01-01"},
        scope=scope
    )
"""

from .base import DBAdapter, QueryResult, ScopeFilter
from .connection_pool import ConnectionPoolManager
from .oracle import OracleAdapter
from .postgresql import PostgreSQLAdapter
from .mysql import MySQLAdapter

__all__ = [
    "DBAdapter",
    "QueryResult",
    "ScopeFilter",
    "ConnectionPoolManager",
    "OracleAdapter",
    "PostgreSQLAdapter",
    "MySQLAdapter",
]
