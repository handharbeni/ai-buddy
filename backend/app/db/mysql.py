"""MySQL database adapter for BAPENDA Local AI Platform."""
import aiomysql
import asyncio
import time
from typing import Dict, List, Any, Optional
from .base import DBAdapter, QueryResult, ScopeFilter


class MySQLAdapter(DBAdapter):
    """MySQL database adapter using aiomysql."""

    def __init__(self, dsn: str, username: str = "AI_READONLY", password: str = ""):
        self.dsn = dsn
        self.username = username
        self.password = password
        self.pool = None
        self.initialized = False

    async def _initialize_pool(self) -> None:
        """Initialize the MySQL connection pool."""
        if not self.initialized:
            # Parse DSN: mysql://user:pass@host:port/db
            import urllib.parse
            parsed = urllib.parse.urlparse(self.dsn)
            
            self.pool = await aiomysql.create_pool(
                host=parsed.hostname or "localhost",
                port=parsed.port or 3306,
                user=self.username,
                password=self.password,
                db=parsed.path.lstrip("/") if parsed.path else None,
                minsize=2,
                maxsize=10,
                autocommit=True,
                charset="utf8mb4",
                connect_timeout=10,
            )
            self.initialized = True

    async def _get_connection(self):
        """Get a connection from the pool."""
        if not self.initialized:
            await self._initialize_pool()
        return await self.pool.acquire()

    async def _release_connection(self, conn) -> None:
        """Release a connection back to the pool."""
        self.pool.release(conn)

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        scope: Optional[ScopeFilter] = None,
        timeout: Optional[int] = None,
        row_limit: Optional[int] = None,
    ) -> QueryResult:
        """Execute a query against MySQL database."""
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

        # Enforce row limit (MySQL uses LIMIT)
        if "LIMIT" not in query.upper():
            query = f"{query} LIMIT {row_limit}"

        # Execute query with timeout
        try:
            conn = await self._get_connection()
            try:
                async with conn.cursor() as cursor:
                    # Use asyncio.wait_for for timeout
                    async def _execute():
                        if params:
                            # Convert dict to positional params
                            await cursor.execute(query, list(params.values()))
                        else:
                            await cursor.execute(query)
                        rows = await cursor.fetchall()
                        columns = [desc[0].lower() for desc in cursor.description]
                        return rows, columns
                    
                    rows, columns = await asyncio.wait_for(_execute(), timeout=timeout)
                    
                    # Convert to list of dicts
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    # Get row count
                    row_count = len(data)
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    return QueryResult(
                        data=data,
                        meta={
                            "query_id": f"mysql_{hash(query) % 1000000}",
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
        """Check MySQL database connectivity."""
        try:
            conn = await self._get_connection()
            try:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    await cursor.fetchone()
                await self._release_connection(conn)
                return {
                    "status": "healthy",
                    "database": "mysql",
                }
            except Exception as e:
                await self._release_connection(conn)
                return {
                    "status": "unhealthy",
                    "database": "mysql",
                    "error": str(e),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "mysql",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the MySQL connection pool."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.initialized = False