"""Tests for Oracle database adapter."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.db.oracle import OracleAdapter
from app.db.base import QueryResult, ScopeFilter


@pytest.fixture
def mock_oracle_pool():
    """Create a mock Oracle connection pool."""
    pool = AsyncMock()
    conn = AsyncMock()
    cursor = AsyncMock()
    
    pool.acquire = AsyncMock(return_value=conn)
    conn.cursor = AsyncMock(return_value=cursor)
    cursor.description = [
        ("PERIOD", None, None, None, None, None, None),
        ("REGION_CODE", None, None, None, None, None, None),
        ("TAX_TYPE", None, None, None, None, None, None),
        ("TARGET", None, None, None, None, None, None),
        ("REALIZATION", None, None, None, None, None, None),
        ("PERCENTAGE", None, None, None, None, None, None),
    ]
    cursor.fetchall = AsyncMock(return_value=[
        ("2025-01-01", "3201", "PBB", 100000000.0, 85000000.0, 85.0),
    ])
    cursor.execute = AsyncMock()
    
    return pool, conn, cursor


@pytest.mark.asyncio
async def test_oracle_adapter_execute_query(mock_oracle_pool):
    """Test Oracle adapter query execution."""
    pool, conn, cursor = mock_oracle_pool
    
    adapter = OracleAdapter(
        dsn="localhost:1521/ORCL",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    result = await adapter.execute_query(
        query="SELECT * FROM V_TAX_REVENUE_SCOPE WHERE period_start = :period",
        params={"period": "2025-01-01"},
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    assert isinstance(result, QueryResult)
    assert result.row_count == 1
    assert result.data[0]["period"] == "2025-01-01"
    assert result.data[0]["tax_type"] == "PBB"


@pytest.mark.asyncio
async def test_oracle_adapter_scope_filter():
    """Test scope filter is applied to query."""
    pool, conn, cursor = mock_oracle_pool
    
    adapter = OracleAdapter(
        dsn="localhost:1521/ORCL",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    await adapter.execute_query(
        query="SELECT * FROM V_TAX_REVENUE_SCOPE",
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    # Verify scope filter was added to query
    call_args = cursor.execute.call_args
    executed_query = call_args[0][0]
    assert "REGION_CODE IN ('3201')" in executed_query
    assert "TAX_TYPE IN ('PBB')" in executed_query


@pytest.mark.asyncio
async def test_oracle_adapter_timeout():
    """Test query timeout enforcement."""
    pool, conn, cursor = mock_oracle_pool
    
    adapter = OracleAdapter(
        dsn="localhost:1521/ORCL",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    cursor.execute = AsyncMock(side_effect=asyncio.TimeoutError())
    
    with pytest.raises(TimeoutError):
        await adapter.execute_query(
            query="SELECT * FROM V_TAX_REVENUE_SCOPE",
            timeout=1,
        )


@pytest.mark.asyncio
async def test_oracle_adapter_row_limit():
    """Test row limit is enforced."""
    pool, conn, cursor = mock_oracle_pool
    
    adapter = OracleAdapter(
        dsn="localhost:1521/ORCL",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    await adapter.execute_query(
        query="SELECT * FROM V_TAX_REVENUE_SCOPE",
        row_limit=100,
    )
    
    call_args = cursor.execute.call_args
    executed_query = call_args[0][0]
    assert "FETCH FIRST 100 ROWS ONLY" in executed_query


@pytest.mark.asyncio
async def test_oracle_adapter_health_check(mock_oracle_pool):
    """Test health check."""
    pool, conn, cursor = mock_oracle_pool
    
    adapter = OracleAdapter(
        dsn="localhost:1521/ORCL",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = pool
    adapter.initialized = True
    
    cursor.fetchone = AsyncMock(return_value=(1,))
    
    result = await adapter.health_check()
    
    assert result["status"] == "healthy"
    assert result["database"] == "oracle"


@pytest.mark.asyncio
async def test_oracle_adapter_close():
    """Test closing the pool."""
    adapter = OracleAdapter(
        dsn="localhost:1521/ORCL",
        username="AI_READONLY",
        password="test_pass"
    )
    adapter.pool = AsyncMock()
    adapter.initialized = True
    
    await adapter.close()
    
    adapter.pool.close.assert_called_once_with(force=True)
    assert not adapter.initialized