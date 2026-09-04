"""Oracle database adapter for BAPENDA Local AI Platform."""
import oracledb
import asyncio
from typing import Dict, List, Any, Optional
from .base import DBAdapter, QueryResult, ScopeFilter


class OracleAdapter(DBAdapter):
    """Oracle database adapter using python-oracledb in async mode.

    Authentication: pass `dsn`, `username`, `password` directly,
    or use `OracleAdapter.from_config("batamai")` to load from app.config.
    """

    def __init__(self, dsn: str, username: str, password: str):
        self.dsn = dsn
        self.username = username
        self.password = password
        self.pool = None
        self.initialized = False

    @classmethod
    def from_config(cls, db_name: str = "batamai"):
        """Build an OracleAdapter from DATABASE_CONFIGS in app.config.

        Args:
            db_name: Key into DATABASE_CONFIGS["oracle"] (e.g., "batamai").

        Returns:
            OracleAdapter instance ready to use.

        Raises:
            ValueError: If db_name not found or password env var missing.
        """
        import os
        from app.config import get_db_config, get_all_db_configs

        cfg = get_db_config("oracle", db_name)
        if cfg is None:
            raise ValueError(
                f"Oracle database '{db_name}' not found in config. "
                f"Available: {list(get_all_db_configs('oracle').keys())}"
            )

        password_env = cfg.get("password_env", "ORACLE_BATAMAI_PASSWORD")
        password = os.environ.get(password_env) or cfg.get("password")
        if not password:
            raise ValueError(
                f"Oracle password not set. Export env var: {password_env}=<password>"
            )

        host = cfg["host"]
        port = cfg["port"]
        service_name = cfg["service_name"]
        user = cfg["user"]

        # Easy Connect string format: host:port/service_name
        dsn = oracledb.makedsn(host, port, service_name=service_name)
        return cls(dsn=dsn, username=user, password=password)

    async def _initialize_pool(self) -> None:
        """Initialize the Oracle connection pool."""
        if not self.initialized:
            self.pool = await oracledb.create_pool_async(
                user=self.username,
                password=self.password,
                dsn=self.dsn,
                min=2,
                max=10,
                increment=1,
                timeout=1800,  # 30 minutes
                retry_limit=3,
                retry_delay=1,
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
        """Execute a query against Oracle database."""
        import time
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

        # Enforce row limit
        if "LIMIT" not in query.upper():
            query = f"{query} FETCH FIRST {row_limit} ROWS ONLY"

        # Execute query with timeout
        try:
            conn = await self._get_connection()
            try:
                cursor = await conn.cursor()
                # Set query timeout
                await cursor.execute(f"ALTER SESSION SET timeout = {timeout * 1000}")
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)
                
                # Fetch results
                columns = [desc[0].lower() for desc in cursor.description]
                rows = await cursor.fetchall()
                
                # Convert to list of dicts
                data = [dict(zip(columns, row)) for row in rows]
                
                # Get row count
                row_count = len(data)
                
                latency_ms = (time.time() - start_time) * 1000
                
                return QueryResult(
                    data=data,
                    meta={
                        "query_id": f"oracle_{hash(query) % 1000000}",
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
            # Log the error without exposing sensitive info
            raise RuntimeError(f"Database error: {str(e)}") from e

    async def health_check(self) -> Dict[str, Any]:
        """Check Oracle database connectivity."""
        try:
            conn = await self._get_connection()
            try:
                cursor = await conn.cursor()
                await cursor.execute("SELECT 1 FROM dual")
                result = await cursor.fetchone()
                await self._release_connection(conn)
                return {
                    "status": "healthy",
                    "database": "oracle",
                    "response_time_ms": 0,  # We don't measure here for simplicity
                }
            except Exception as e:
                await self._release_connection(conn)
                return {
                    "status": "unhealthy",
                    "database": "oracle",
                    "error": str(e),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "oracle",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the Oracle connection pool."""
        if self.pool:
            await self.pool.close(force=True)
            self.initialized = False