"""Tests for MySQL database adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.db.mysql import MySQLAdapter
from app.db.base import QueryResult, ScopeFilter


@pytest.fixture
def mock_mysql_pool():
    """Create a mock MySQL connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    
    pool.acquire = AsyncMock(return_value=conn)
    conn.cursor = AsyncMock()
    conn.cursor.__aenter__ = AsyncMock(return_value=conn.cursor())
    conn.cursor.__aexit__ = AsyncMock(return_value=None)
    conn.cursor.fetchall = AsyncMock(return_value=[
        {"period": "2025-01-01", "region_code": "3201", "tax_type": "PBB", "target": 100000000.0, "realization": 85000000.0, "percentage": 85.0}
    ])
    conn.cursor.fetchone = AsyncMock(return_value=None)
    
    return pool, conn


@pytest.mark.asyncio
async def test_mysql_adapter_execute_query(mock_mysql_pool):
    """Test MySQL adapter query execution."""
    pool, conn = mock_mysql_pool
    
    adapter = MySQLAdapter(
        dsn="localhost:3306/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    result = await adapter.execute_query(
        query="SELECT * FROM v_tax_revenue_scope WHERE period_start = %s",
        params=("2025-01-01",),
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    assert isinstance(result, QueryResult)
    assert result.row_count == 1
    assert result.data[0]["period"] == "2025-01-01"


@pytest.mark.asyncio
async def test_mysql_adapter_scope_filter(mock_mysql_pool):
    """Test scope filter is applied to query."""
    pool, conn = mock_mysql_pool
    
    adapter = MySQLAdapter(
        dsn="localhost:3306/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    await adapter.execute_query(
        query="SELECT * FROM v_tax_revenue_scope",
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    # Verify scope filter was added
    call_args = conn.cursor.execute.call_args
    executed_query = call_args[0][0]
    assert "region_code IN ('3201')" in executed_query


@pytest.mark.asyncio
async def test_mysql_adapter_timeout(mock_mysql_pool):
    """Test query timeout enforcement."""
    pool, conn = mock_mysql_pool
    
    adapter = MySQLAdapter(
        dsn="localhost:3306/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    conn.cursor.execute = AsyncMock(side_effect=asyncio.TimeoutError())
    
    with pytest.raises(TimeoutError):
        await adapter.execute_query(
            query="SELECT * FROM v_tax_revenue_scope",
            timeout=1,
        )


@pytest.mark.asyncio
async def test_mysql_adapter_row_limit(mock_mysql_pool):
    """Test row limit is enforced."""
    pool, conn = mock_mysql_pool
    
    adapter = MySQLAdapter(
        dsn="localhost:3306/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    await adapter.execute_query(
        query="SELECT * FROM v_tax_revenue_scope",
        row_limit=100,
    )
    
    call_args = conn.cursor.execute.call_args
    executed_query = call_args[0][0]
    assert "LIMIT 100" in executed_query


@pytest.mark.asyncio
async def test_mysql_adapter_health_check(mock_mysql_pool):
    """Test health check."""
    pool, conn = mock_mysql_pool
    
    adapter = MySQLAdapter(
        dsn="localhost:3306/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    conn.cursor.execute = AsyncMock(return_value=None)
    conn.cursor.fetchone = AsyncMock(return_value=(1,))
    
    result = await adapter.health_check()
    
    assert result["status"] == "healthy"
    assert result["database"] == "mysql"


@pytest.mark.asyncio
async def test_mysql_adapter_close():
    """Test closing the pool."""
    adapter = MySQLAdapter(
        dsn="localhost:3306/bapenda",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = AsyncMock()
    adapter.initialized = True
    
    await adapter.close()
    
    adapter.pool.close.assert_called_once()
    assert not adapter.initialized