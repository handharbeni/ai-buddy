"""Shared test fixtures for database adapters."""

import pytest
from app.db.base import ScopeFilter


@pytest.fixture
def staff_scope():
    """Scope for a staff user."""
    return ScopeFilter(
        user_id="STAFF_001",
        role="STAFF",
        regions=["3201"],
        tax_types=["PBB", "BPHTB"],
    )


@pytest.fixture
def analyst_scope():
    """Scope for an analyst user."""
    return ScopeFilter(
        user_id="ANALYST_001",
        role="ANALYST",
        regions=["3201", "3202"],
        tax_types=["PBB"],
    )


@pytest.fixture
def supervisor_scope():
    """Scope for a supervisor user."""
    return ScopeFilter(
        user_id="SUPV_001",
        role="SUPERVISOR",
        regions=["3201"],
        tax_types=["PBB", "BPHTB", "PPh"],
    )


@pytest.fixture
def admin_scope():
    """Scope for an admin user."""
    return ScopeFilter(
        user_id="ADMIN_001",
        role="ADMIN",
        regions=None,  # All regions
        tax_types=None,  # All tax types
    )


@pytest.fixture
def mock_adapter():
    """Create a mock adapter instance."""
    from app.db.mocks import MockAdapter
    return MockAdapter()