"""PostgreSQL database adapter for BAPENDA Local AI Platform."""
import asyncpg
import asyncio
import time
from typing import Dict, List, Any, Optional
from .base import DBAdapter, QueryResult, ScopeFilter


class PostgreSQLAdapter(DBAdapter):
    """PostgreSQL database adapter using asyncpg."""

    def __init__(self, dsn: str = "", username: str = "AI_READONLY", password: str = "", host: str = "", port: int = 5432):
        self.username = username
        self.password = password
        self.pool = None
        self.initialized = False
        # Build DSN from components if host provided, else use raw dsn
        if host:
            db = dsn if dsn else "app_db"
            self.conn_str = f"postgresql://{username}:{password}@{host}:{port}/{db}"
        elif "://" in dsn:
            self.conn_str = dsn
        else:
            self.conn_str = f"postgresql://{username}:{password}@{dsn}"

    async def _initialize_pool(self) -> None:
        """Initialize the PostgreSQL connection pool."""
        if not self.initialized:
            self.pool = await asyncpg.create_pool(
                dsn=self.conn_str,
                min_size=2,
                max_size=10,
                command_timeout=1800,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
            )
            self.initialized = True

    async def _get_connection(self):
        """Get a connection from the pool."""
        if not self.initialized:
            await self._initialize_pool()
        return await self.pool.acquire()

    async def _release_connection(self, conn) -> None:
        """Release a connection back to the pool."""
        await self.pool.release(conn)

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        scope: Optional[ScopeFilter] = None,
        timeout: Optional[int] = None,
        row_limit: Optional[int] = None,
    ) -> QueryResult:
        """Execute a query against PostgreSQL database."""
        start_time = time.time()

        # Use defaults if not provided
        timeout = timeout or self.DEFAULT_TIMEOUT
        row_limit = row_limit or self.DEFAULT_ROW_LIMIT

        # Apply scope filters to the query
        scope_where = self._build_scope_filter(scope)
        if scope_where:
            # If the query already has a WHERE clause, append with AND
            if "WHERE" in query.upper():
                query = f"{query} AND {scope_where}"
            else:
                query = f"{query} WHERE {scope_where}"

        # Enforce row limit (PostgreSQL uses LIMIT)
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {row_limit}"

        # Execute query with timeout
        try:
            conn = await self._get_connection()
            try:
                # Use asyncio.wait_for for timeout
                async def _execute():
                    if params:
                        # Convert dict to positional params for asyncpg
                        rows = await conn.fetch(query, *params.values())
                    else:
                        rows = await conn.fetch(query)
                    return rows
                
                rows = await asyncio.wait_for(_execute(), timeout=timeout)
                
                # Convert to list of dicts
                data = [dict(row) for row in rows]
                
                # Get row count
                row_count = len(data)
                
                latency_ms = (time.time() - start_time) * 1000
                
                return QueryResult(
                    data=data,
                    meta={
                        "query_id": f"postgresql_{hash(query) % 1000000}",
                        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "scope_applied": scope.dict() if scope else {},
                    },
                    row_count=row_count,
                    latency_ms=latency_ms,
                )
            finally:
                await self._release_connection(conn)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Query exceeded {timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Database error: {str(e)}") from e

    async def health_check(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity."""
        try:
            conn = await self._get_connection()
            try:
                await conn.fetchval("SELECT 1")
                await self._release_connection(conn)
                return {
                    "status": "healthy",
                    "database": "postgresql",
                }
            except Exception as e:
                await self._release_connection(conn)
                return {
                    "status": "unhealthy",
                    "database": "postgresql",
                    "error": str(e),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "postgresql",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            self.initialized = False