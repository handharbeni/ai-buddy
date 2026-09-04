"""Tests for PostgreSQL database adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.db.postgresql import PostgreSQLAdapter
from app.db.base import QueryResult, ScopeFilter


@pytest.fixture
def mock_postgres_pool():
    """Create a mock PostgreSQL connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    
    pool.acquire = AsyncMock(return_value=conn)
    conn.fetch = AsyncMock(return_value=[
        {"period": "2025-01-01", "region_code": "3201", "tax_type": "PBB", "target": 100000000.0, "realization": 85000000.0, "percentage": 85.0}
    ])
    
    return pool, conn


@pytest.mark.asyncio
async def test_postgres_adapter_execute_query(mock_postgres_pool):
    """Test PostgreSQL adapter query execution."""
    pool, conn = mock_postgres_pool
    
    adapter = PostgreSQLAdapter(
        dsn="localhost:5432/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    result = await adapter.execute_query(
        query="SELECT * FROM v_tax_revenue_scope WHERE period_start = $1",
        params={"1": "2025-01-01"},
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    assert isinstance(result, QueryResult)
    assert result.row_count == 1
    assert result.data[0]["period"] == "2025-01-01"
    assert result.data[0]["tax_type"] == "PBB"


@pytest.mark.asyncio
async def test_postgres_adapter_scope_filter(mock_postgres_pool):
    """Test scope filter is applied to query."""
    pool, conn = mock_postgres_pool
    
    adapter = PostgreSQLAdapter(
        dsn="localhost:5432/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    await adapter.execute_query(
        query="SELECT * FROM v_tax_revenue_scope",
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    # Verify scope filter was added to query
    call_args = conn.fetch.call_args
    executed_query = call_args[0][0]
    assert "region_code IN ('3201')" in executed_query
    assert "tax_type IN ('PBB')" in executed_query


@pytest.mark.asyncio
async def test_postgres_adapter_timeout(mock_postgres_pool):
    """Test query timeout enforcement."""
    pool, conn = mock_postgres_pool
    
    adapter = PostgreSQLAdapter(
        dsn="localhost:5432/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    conn.fetch = AsyncMock(side_effect=asyncio.TimeoutError())
    
    with pytest.raises(TimeoutError):
        await adapter.execute_query(
            query="SELECT * FROM v_tax_revenue_scope",
            timeout=1,
        )


@pytest.mark.asyncio
async def test_postgres_adapter_row_limit(mock_postgres_pool):
    """Test row limit is enforced."""
    pool, conn = mock_postgres_pool
    
    adapter = PostgreSQLAdapter(
        dsn="localhost:5432/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    await adapter.execute_query(
        query="SELECT * FROM v_tax_revenue_scope",
        row_limit=100,
    )
    
    call_args = conn.fetch.call_args
    executed_query = call_args[0][0]
    assert "LIMIT 100" in executed_query


@pytest.mark.asyncio
async def test_postgres_adapter_health_check(mock_postgres_pool):
    """Test health check."""
    pool, conn = mock_postgres_pool
    
    adapter = PostgreSQLAdapter(
        dsn="localhost:5432/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    conn.fetchval = AsyncMock(return_value=1)
    
    result = await adapter.health_check()
    
    assert result["status"] == "healthy"
    assert result["database"] == "postgresql"


@pytest.mark.asyncio
async def test_postgres_adapter_close():
    """Test closing the pool."""
    adapter = PostgreSQLAdapter(
        dsn="localhost:5432/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = AsyncMock()
    adapter.initialized = True
    
    await adapter.close()
    
    adapter.pool.close.assert_called_once()
    assert not adapter.initialized