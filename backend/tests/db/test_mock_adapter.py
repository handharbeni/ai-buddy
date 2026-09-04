"""Tests for mock database adapter."""

import pytest

from app.db.mocks import MockAdapter
from app.db.base import QueryResult, ScopeFilter


@pytest.fixture
def mock_adapter():
    """Create a mock adapter instance."""
    return MockAdapter()


@pytest.mark.asyncio
async def test_mock_adapter_execute_query(mock_adapter):
    """Test mock adapter query execution."""
    result = await mock_adapter.execute_query(
        query="SELECT * FROM tax_revenue",
    )
    
    assert isinstance(result, QueryResult)
    assert result.row_count > 0
    assert result.data[0]["period"] == "2025-01-01"


@pytest.mark.asyncio
async def test_mock_adapter_scope_filter(mock_adapter):
    """Test scope filter is applied to mock data."""
    result = await mock_adapter.execute_query(
        query="SELECT * FROM tax_revenue",
        scope=ScopeFilter(user_id="test", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    # Should only return data for region 3201 and tax_type PBB
    for row in result.data:
        assert row["region_code"] == "3201"
        assert row["tax_type"] == "PBB"


@pytest.mark.asyncio
async def test_mock_adapter_row_limit(mock_adapter):
    """Test row limit is enforced."""
    result = await mock_adapter.execute_query(
        query="SELECT * FROM tax_revenue",
        row_limit=1,
    )
    
    assert result.row_count == 1


@pytest.mark.asyncio
async def test_mock_adapter_health_check(mock_adapter):
    """Test health check."""
    result = await mock_adapter.health_check()
    
    assert result["status"] == "healthy"
    assert result["database"] == "mock"


@pytest.mark.asyncio
async def test_mock_adapter_close(mock_adapter):
    """Test close does nothing."""
    await mock_adapter.close()  # Should not raise