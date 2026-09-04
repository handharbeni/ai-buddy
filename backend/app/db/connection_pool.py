"""Connection pool manager for database adapters."""

import asyncio
from typing import Any, Dict, Optional


class ConnectionPoolManager:
    """Manages connection pools for all database types."""

    def __init__(self):
        self.pools: Dict[str, Any] = {}

    async def get_pool(self, db_type: str, config: Dict[str, Any]):
        """Get or create a connection pool for a database type."""
        if db_type not in self.pools:
            pool = await self._create_pool(db_type, config)
            self.pools[db_type] = pool
        return self.pools[db_type]

    async def _create_pool(self, db_type: str, config: Dict[str, Any]):
        """Create a connection pool based on database type."""
        if db_type == "oracle":
            import oracledb
            return await oracledb.create_pool_async(
                user=config["username"],
                password=config["password"],
                dsn=config["dsn"],
                min=2,
                max=10,
                increment=1,
                timeout=1800,
                retry_limit=3,
                retry_delay=1,
            )
        elif db_type == "postgresql":
            import asyncpg
            return await asyncpg.create_pool(
                dsn=config["dsn"],
                min_size=2,
                max_size=10,
                command_timeout=1800,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
            )
        elif db_type == "mysql":
            import aiomysql
            return await aiomysql.create_pool(
                host=config["host"],
                port=config.get("port", 3306),
                user=config["username"],
                password=config["password"],
                db=config.get("database"),
                minsize=2,
                maxsize=10,
                autocommit=True,
                charset="utf8mb4",
                connect_timeout=10,
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    async def close_all(self):
        """Close all connection pools."""
        for db_type, pool in self.pools.items():
            if db_type == "oracle":
                await pool.close(force=True)
            elif db_type == "postgresql":
                await pool.close()
            elif db_type == "mysql":
                pool.close()
                await pool.wait_closed()
        self.pools.clear()