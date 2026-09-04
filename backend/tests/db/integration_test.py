"""Tests for database adapters integration."""

import pytest

from app.db.mocks import MockAdapter
from app.db.base import QueryResult, ScopeFilter


@pytest.mark.asyncio
async def test_mock_adapter_tax_revenue():
    """Test revenue data query."""
    adapter = MockAdapter()
    
    result = await adapter.execute_query(
        query="SELECT period, region_code, tax_type, target, realization, percentage FROM tax_revenue",
        scope=ScopeFilter(user_id="STAFF_001", role="STAFF", regions=["3201"], tax_types=["PBB"]),
    )
    
    assert result.row_count == 1
    assert result.data[0]["region_code"] == "3201"
    assert result.data[0]["tax_type"] == "PBB"
    assert result.data[0]["percentage"] == 85.0


@pytest.mark.asyncio
async def test_mock_adapter_tax_arrears():
    """Test arrears data query."""
    adapter = MockAdapter()
    
    result = await adapter.execute_query(
        query="SELECT taxpayer_id, taxpayer_name, region_code, tax_type, arrears_amount FROM tax_arrears",
        scope=ScopeFilter(user_id="STAFF_001", role="STAFF", regions=["3201"]),
    )
    
    assert result.row_count == 2
    for row in result.data:
        assert row["region_code"] == "3201"


@pytest.mark.asyncio
async def test_mock_adapter_growth_statistics():
    """Test growth statistics query."""
    adapter = MockAdapter()
    
    result = await adapter.execute_query(
        query="SELECT region_code, tax_type, period, yoy_growth, target_achievement FROM growth_statistics",
        scope=ScopeFilter(user_id="ANALYST_001", role="ANALYST", regions=["3201", "3202"]),
    )
    
    assert result.row_count == 2
    assert result.data[0]["yoy_growth"] == 5.2


@pytest.mark.asyncio
async def test_mock_adapter_no_scope():
    """Test query without scope returns all data."""
    adapter = MockAdapter()
    
    result = await adapter.execute_query(
        query="SELECT * FROM tax_revenue",
    )
    
    assert result.row_count == 2  # All regions in mock data


@pytest.mark.asyncio
async def test_mock_adapter_cross_region_scope():
    """Test scope filters prevent cross-region access."""
    adapter = MockAdapter()
    
    result = await adapter.execute_query(
        query="SELECT * FROM tax_revenue",
        scope=ScopeFilter(user_id="STAFF_001", role="STAFF", regions=["3201"]),
    )
    
    # Only region 3201 data should be returned
    for row in result.data:
        assert row["region_code"] == "3201"
    assert result.row_count == 1